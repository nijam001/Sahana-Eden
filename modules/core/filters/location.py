"""
Location Filters

Copyright: 2013-2022 (c) Sahana Software Foundation

Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
"""

__all__ = ("LocationFilter", "MapFilter")

import json
from collections import OrderedDict
from gluon import current, INPUT, SPAN, TAG
from gluon.storage import Storage
from ..tools import JSONSEPARATORS
from ..ui import S3MultiSelectWidget
from .base import FilterWidget
from ..resource import FS, S3ResourceField

# =============================================================================
class LocationFilter(FilterWidget):
    """
    Refactored Hierarchical Location Filter Widget.

    This widget provides:
        - Multi-level hierarchical location selection
        - Dynamic options loading from database or predefined options
        - Translation support
        - Multi-select dropdowns
        - Pre-selected values support
        - Automatic JS injection for dependent level activation
    """

    css_base = "location-filter"
    operator = "belongs"

    # -------------------------------------------------------------------------
    def __init__(self, field=None, **attr):
        """
        Initialize the LocationFilter widget.
        """
        if not field:
            field = "location_id"

        settings = current.deployment_settings
        translate = settings.get_L10n_translate_gis_location()
        if translate and current.session.s3.language == "en":
            translate = False
        self.translate = translate

        super().__init__(field=field, **attr)

        if "label" not in self.opts:
            self.opts.label = current.T("Filter by Location")

        self._levels = None

    # -------------------------------------------------------------------------
    def widget(self, resource, values):
        """
        Render the full filter widget with multi-level selectors.
        """
        ftype, levels, noopt = self._options(resource, values=values)
        if noopt:
            return SPAN(noopt, _class="no-options-available")

        attr = self._attr(resource)
        css_class = self._get_css_class(attr)
        header_opt = self._resolve_header_option()
        base_id, base_name = attr["_id"], attr["_name"]

        widgets = []
        for idx, level in enumerate(levels):
            widgets.append(
                self._render_level_widget(levels, level, idx, values, css_class,
                                          header_opt, base_id, base_name, ftype)
            )

        return TAG[""](*widgets)

    # -------------------------------------------------------------------------
    def _get_css_class(self, attr):
        """
        Determine the CSS class for the container based on attributes.
        """
        css = attr.get("class")
        _class = f"{css} {self.css_base}" if css else self.css_base
        if "multiselect-filter-widget" not in _class:
            _class += " multiselect-filter-widget"
        if not self.opts.get("hidden") and "active" not in _class:
            _class += " active"
        return _class

    # -------------------------------------------------------------------------
    def _resolve_header_option(self):
        """
        Determine whether to show the multiselect header.
        """
        header_opt = self.opts.get("header", False)
        if header_opt is True or header_opt is False:
            setting = current.deployment_settings.get_ui_location_filter_bulk_select_option()
            if setting is not None:
                header_opt = setting
        return header_opt

    # -------------------------------------------------------------------------
    def _render_level_widget(self, levels, level, index, values, css_class,
                             header_opt, base_id, base_name, ftype):
        """
        Render a single multiselect widget for a hierarchy level.
        """
        w_attr = dict(self._attr(None))
        w_attr["_id"] = f"{base_id}-{level}"
        w_attr["_name"] = name = f"{base_name}-{level}"

        dummy_field = Storage(name=name, type=ftype)
        level_values = values.get(f"{self._prefix(self.field)}${level}__{self.operator}")
        placeholder = current.T("Select %(location)s") % {"location": levels[level]["label"]}

        widget = S3MultiSelectWidget(
            search=self.opts.get("search", "auto"),
            header=header_opt,
            selectedList=self.opts.get("selectedList", 3),
            noneSelectedText=placeholder,
        )

        if index == 0:
            w_attr["_class"] = css_class
            dummy_field.requires = self._build_requirements(levels[level])
            return widget(dummy_field, level_values, **w_attr)
        else:
            w_attr["_class"] = f"{css_class} hide"
            jquery_ready = current.response.s3.jquery_ready
            current.response.s3.jquery_ready = []

            dummy_field.requires = self._build_requirements({})
            w_out = widget(dummy_field, level_values, **w_attr)

            # Extract the activation JS script
            script = current.response.s3.jquery_ready[0] if current.response.s3.jquery_ready else ""
            current.response.s3.jquery_ready = jquery_ready
            script = f"S3.{name.replace('-', '_')}=function(){{{script}}}"
            current.response.s3.js_global.append(script)
            return w_out

    # -------------------------------------------------------------------------
    def _build_requirements(self, level_opts):
        """
        Build requirements for multiselect field.
        """
        from gluon.validators import IS_IN_SET
        options = level_opts.get("options", [])
        return IS_IN_SET(options, multiple=True)

    # -------------------------------------------------------------------------
    @property
    def levels(self):
        """
        Initialize and return the hierarchical levels as an OrderedDict.
        """
        if self._levels is None:
            opts = self.opts
            hierarchy = current.gis.get_location_hierarchy()
            if "levels" in opts:
                self._levels = OrderedDict(
                    (level, hierarchy.get(level, level)) for level in opts.levels
                )
            else:
                self._levels = current.gis.get_relevant_hierarchy_levels(as_dict=True)

            # Initialize options containers
            for level in self._levels:
                self._levels[level] = {"label": self._levels[level],
                                       "options": {} if self.translate else []}
        return self._levels

    # -------------------------------------------------------------------------
    def _options(self, resource, values=None, inject_hierarchy=True):
        """
        Generate all options for the widget, including hierarchy and translations.
        """
        s3db = current.s3db
        opts = self.opts
        ftype = "reference gis_location"
        levels = self.levels
        no_opts = opts.get("no_opts") or current.T("No options available")
        default = (ftype, levels, no_opts)

        # Determine resource/selector
        selector = None
        if resource is None:
            rname = opts.get("resource")
            if rname:
                resource = s3db.resource(rname)
                selector = opts.get("lookup", "location_id")
        else:
            selector = self.field

        filters_added = False
        options = opts.get("options")
        if options:
            resource = s3db.resource("gis_location", id=options)
        elif selector:
            rfield = S3ResourceField(resource, selector)
            if not rfield.field or rfield.ftype != ftype:
                raise TypeError(f"invalid selector: {selector}")
            resource.add_filter(FS(selector) != None)
            resource.add_filter(FS(f"{selector}$end_date") == None)
            filters_added = True
        else:
            return default

        # Fetch rows
        rows = self._lookup_options(levels, resource, selector, options, self.translate)

        if filters_added:
            resource.rfilter.filters.pop()
            resource.rfilter.filters.pop()
            resource.rfilter.query = None
            resource.rfilter.transformed = None

        # Ensure pre-selected values are included
        if values:
            rows = self._add_selected(rows, values, levels, self.translate)

        if not rows:
            return default

        local_names = self._get_local_names(rows) if self.translate else {}

        # Build hierarchy
        toplevel = list(levels.keys())[0]
        hierarchy = {toplevel: {}}
        for row in rows:
            h = hierarchy[toplevel]
            for level in levels:
                name = row.get(level)
                if not name:
                    continue
                opts_level = levels[level]["options"]
                if name not in opts_level:
                    if self.translate:
                        opts_level[name] = local_names.get(name, name)
                    else:
                        opts_level.append(name)
                if inject_hierarchy:
                    if name not in h:
                        h[name] = {}
                    h = h[name]

        self._sort_options(levels, translate=self.translate)

        if inject_hierarchy:
            js_global = current.response.s3.js_global
            jsons = lambda v: json.dumps(v, separators=JSONSEPARATORS)
            js_global.append(f"S3.location_filter_hierarchy={jsons(hierarchy)}")
            if self.translate:
                js_global.append(f"S3.location_name_l10n={jsons(local_names)}")

        return (ftype, levels, None)

    # -------------------------------------------------------------------------
    def _lookup_options(self, levels, resource, selector, options, translate):
        """
        Query the database or provided options to retrieve selectable items.
        """
        rows = []
        if options:
            for option_id in options:
                row = {level: option_id for level in levels}
                rows.append(row)
        else:
            rows = resource.select([selector] + list(levels.keys())).rows
        return rows

    # -------------------------------------------------------------------------
    def _add_selected(self, rows, values, levels, translate):
        """
        Ensure pre-selected values are present in options.

        Args:
            rows (list of dict): Existing rows from resource
            values (dict): User-selected values
            levels (OrderedDict): Hierarchy levels
            translate (bool): Whether to apply translations

        Returns:
            list of dict: Rows including missing selected values
        """
        added = set()
        for level in levels:
            key = f"{self._prefix(self.field)}${level}__{self.operator}"
            selected = values.get(key, [])
            if not isinstance(selected, (list, tuple)):
                selected = [selected]
            for val in selected:
                if val and all(row.get(level) != val for row in rows):
                    # Add missing pre-selected value
                    row = {lvl: None for lvl in levels}
                    row[level] = val
                    rows.append(row)
                    added.add(val)
        return rows

    # -------------------------------------------------------------------------
    def _get_local_names(self, rows):
        """
        Return localized names for translations.
        """
        local_names = {}
        for row in rows:
            for k, v in row.items():
                if v:
                    local_names[v] = current.T(v)
        return local_names

    # -------------------------------------------------------------------------
    def _sort_options(self, levels, translate=False):
        """
        Sort options for each level.
        """
        for level, opts in levels.items():
            if translate:
                levels[level]["options"] = dict(sorted(opts["options"].items()))
            else:
                opts_list = opts["options"]
                opts["options"] = sorted(opts_list) if isinstance(opts_list, list) else opts_list
