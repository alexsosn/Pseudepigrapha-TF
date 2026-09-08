from string import Formatter

from tf.advanced.app import App
from tf.advanced.helpers import parseFeatures


TYPE_POLICIES = {
    "div": {
        "hidden": True,
        "label": "{div_label} {div_number}",
        "featuresBare": "source_ref",
    },
    "unit": {
        "hidden": True,
        "label": "unit {unit_id}",
        "featuresBare": "source_ref",
    },
    "reading": {
        "hidden": True,
        "base": True,
        "template": "{reading_text}",
        "label": "reading {reading_option_source}",
        "features": "is_primary is_omission",
        "featuresBare": "mss",
    },
    "variant_word": {
        "hidden": True,
        "base": True,
        "template": "{prefix_utf8}{g_word_utf8}{trailer_utf8}",
    },
    "manuscript": {
        "hidden": True,
        "base": True,
        "template": "{ms_abbrev}",
        "label": "{ms_abbrev}",
    },
    "resource": {
        "hidden": True,
        "base": True,
        "template": "{resource_name}",
        "label": "{resource_name}",
    },
    "version_metadata": {
        "hidden": True,
        "base": True,
        "template": "{version_title}",
        "label": "{version_title}",
    },
    "ellipsis": {
        "hidden": True,
        "base": True,
        "template": "{ellipsis_text}",
        "label": "{ellipsis_text}",
        "featuresBare": "source_ref",
    },
    "orphan_reading": {
        "hidden": True,
        "base": True,
        "template": "{reading_text}",
        "label": "orphan reading {reading_option_source}",
        "featuresBare": "source_ref",
    },
    "document_metadata": {
        "hidden": True,
        "base": True,
        "template": "{intro_label}",
        "label": "{intro_label}",
    },
}

OWN_CONTENT_TYPES = frozenset(
    node_type for node_type, policy in TYPE_POLICIES.items() if policy.get("base")
)


def _template_spec(template):
    fields = tuple(
        field
        for _, field, _, _ in Formatter().parse(template)
        if field is not None
    )
    return (template, fields)


class TfApp(App):
    """Corpus app with subset-safe display policies for technical TF nodes."""

    def __init__(self, cfg, *args, **kwargs):
        # Text-Fabric reports every typeDisplay key absent from the currently
        # loaded materialization as a configuration error. Pseudepigrapha-TF can
        # materialize subsets in which legitimate node types such as resource,
        # ellipsis, or document_metadata are absent. Keep those policies out of
        # static config validation and install them only when the type exists.
        cfg = dict(cfg)
        static_type_display = dict(cfg.get("typeDisplay", {}))
        for node_type in TYPE_POLICIES:
            static_type_display.pop(node_type, None)
        cfg["typeDisplay"] = static_type_display

        super().__init__(cfg, *args, **kwargs)
        self._install_present_type_policies()
        self.customMethods.plainCustom.update(
            {node_type: self._plain_own_content for node_type in OWN_CONTENT_TYPES}
        )

    def _install_present_type_policies(self):
        if self.api is None:
            return

        present_types = set(self.api.F.otype.all)
        available_features = set(self.api.Fall(warp=False))
        context = self.context
        applied = {}

        for node_type, policy in TYPE_POLICIES.items():
            if node_type not in present_types:
                continue

            applied[node_type] = dict(policy)
            if policy.get("base"):
                context.baseTypes.add(node_type)
            if policy.get("hidden"):
                context.hiddenTypes.add(node_type)

            for key, destination in (
                ("template", context.templates),
                ("label", context.labels),
            ):
                value = policy.get(key)
                if value is not None:
                    destination[node_type] = _template_spec(value)

            for key, destination in (
                ("features", context.features),
                ("featuresBare", context.featuresBare),
            ):
                value = policy.get(key)
                if value:
                    present_value = " ".join(
                        feature
                        for feature in value.split()
                        if feature in available_features
                    )
                    destination[node_type] = parseFeatures(present_value)

        # Keep diagnostic/showContext state aligned with the policies actually
        # active for this materialization. The mutable context sets/dicts are the
        # same objects captured by TF display defaults, so updates apply to
        # subsequent plain/pretty rendering without rebuilding the app.
        self.cfgSpecs.setdefault("typeDisplay", {}).update(applied)

    def _plain_own_content(self, options, chunk, node_type, outer):
        """Render only a technical node's own configured content.

        Text-Fabric 13.1 renders a pretty base non-slot by internally asking for
        a plain rendering of its unravel tree. Without a ``plainCustom`` hook,
        that plain pass continues into the node's oslots children even when an
        explicit template rendered the node itself. For Pseudepigrapha-TF those
        child slots can be locality anchors rather than the node's content.

        Keep the dynamically installed type template authoritative and stop
        recursion here. The one semantic exception is an explicit empty reading:
        make its source omission state visible instead of returning an empty
        string.
        """

        node = chunk[0]
        omission_feature = getattr(self.api.F, "is_omission", None)
        if (
            node_type == "reading"
            and omission_feature is not None
            and omission_feature.v(node) == 1
        ):
            return '<span title="is_omission">[omission]</span>'

        return self.getText(
            False,
            node,
            node_type,
            outer,
            True,
            True,
            0,
            "",
            None,
            options=options,
        )
