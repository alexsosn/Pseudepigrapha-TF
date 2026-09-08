from string import Formatter

from tf.advanced.app import App
from tf.advanced.helpers import parseFeatures


TECHNICAL_TYPES = frozenset(
    {
        "div",
        "unit",
        "reading",
        "variant_word",
        "manuscript",
        "resource",
        "version_metadata",
        "ellipsis",
        "orphan_reading",
        "document_metadata",
    }
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
        # materialize subsets in which legitimate technical node types are absent.
        # Preserve YAML as the single policy source, but postpone those entries
        # until the data has loaded and we know which node types actually exist.
        cfg = dict(cfg)
        requested_type_display = dict(cfg.get("typeDisplay", {}))
        dynamic_policies = {
            node_type: dict(requested_type_display[node_type])
            for node_type in TECHNICAL_TYPES
            if node_type in requested_type_display
        }
        cfg["typeDisplay"] = {
            node_type: policy
            for node_type, policy in requested_type_display.items()
            if node_type not in TECHNICAL_TYPES
        }

        super().__init__(cfg, *args, **kwargs)
        applied_policies = self._install_present_type_policies(dynamic_policies)
        own_content_types = {
            node_type
            for node_type, policy in applied_policies.items()
            if policy.get("base")
        }
        self.customMethods.plainCustom.update(
            {node_type: self._plain_own_content for node_type in own_content_types}
        )

    def _install_present_type_policies(self, policies):
        if self.api is None:
            return {}

        present_types = set(self.api.F.otype.all)
        available_features = set(self.api.Fall())
        context = self.context
        applied = {}

        for node_type, policy in policies.items():
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

            # Match Text-Fabric's native getTypeDefaults() invariant: every
            # configured type gets both feature-display pairs, even when one is
            # empty. Its renderer concatenates the two bare-feature lists and a
            # missing entry falls back to a tuple, which is incompatible with the
            # list returned by parseFeatures() for the populated side.
            for key, destination in (
                ("features", context.features),
                ("featuresBare", context.featuresBare),
            ):
                value = policy.get(key, "")
                present_value = " ".join(
                    feature
                    for feature in value.split()
                    if feature in available_features
                )
                destination[node_type] = parseFeatures(present_value)

        # Restore only active policies in diagnostic/showContext state. The
        # mutable context sets/dicts are the same objects captured by TF display
        # defaults, so these updates affect subsequent rendering immediately.
        self.cfgSpecs.setdefault("typeDisplay", {}).update(applied)
        return applied

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
