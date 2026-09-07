from tf.advanced.app import App


OWN_CONTENT_TYPES = frozenset(
    {
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


class TfApp(App):
    """Corpus app that shields technical oslots anchors from plain rendering."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.customMethods.plainCustom.update(
            {node_type: self._plain_own_content for node_type in OWN_CONTENT_TYPES}
        )

    def _plain_own_content(self, options, chunk, node_type, outer):
        """Render only a technical node's own configured content.

        Text-Fabric 13.1 renders a pretty base non-slot by internally asking for
        a plain rendering of its unravel tree. Without a ``plainCustom`` hook,
        that plain pass continues into the node's oslots children even when an
        explicit template rendered the node itself. For Pseudepigrapha-TF those
        child slots can be locality anchors rather than the node's content.

        Keep the declarative type template authoritative and stop recursion here.
        The one semantic exception is an explicit empty reading: make its source
        omission state visible instead of returning an empty string.
        """

        node = chunk[0]
        if node_type == "reading" and self.api.F.is_omission.v(node) == 1:
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
