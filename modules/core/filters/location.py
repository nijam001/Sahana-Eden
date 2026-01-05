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

from gluon import current, INPUT, SPAN, TAG, IS_IN_SET
from gluon.storage import Storage

from ..resource import FS, S3ResourceField
from ..tools import JSONSEPARATORS
from ..ui import S3MultiSelectWidget
from .base import FilterWidget

# =============================================================================
class LocationFilter(FilterWidget):
    """
    Refactored Hierarchical Location Filter Widget.
    Provides multi-level selection with full parent-lookup and DB translation.
    """

    css_base = "location-filter"
    operator = "belongs"

    def __init__(self, field=None, **attr):
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

    def widget(self, resource, values):
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

    def _get_css_class(self, attr):
        css = attr.get("class")
        _class = f"{css} {self.css_base}" if css else self.css_base
        if "multiselect-filter-widget" not in _class:
            _class += " multiselect-filter-widget"
        if not self.opts.get("hidden") and "active" not in _class:
            _class += " active"
        return _class

    def _resolve_header_option(self):
        header_opt = self.opts.get("header", False)
        if header_opt in (True, False):
            setting = current.deployment_settings.get_ui_location_filter_bulk_select_option()
            if setting is not None:
                header_opt = setting
        return header_opt

    def _render_level_widget(self, levels, level, index, values, css_class,
                             header_opt, base_id, base_name, ftype):
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
            dummy_field.requires = IS_IN_SET(levels[level]["options"], multiple=True)
            return widget(dummy_field, level_values, **w_attr)
        else:
            w_attr["_class"] = f"{css_class} hide"
            s3 = current.response.s3
            jquery_ready = s3.jquery_ready
            s3.jquery_ready = []

            dummy_field.requires = IS_IN_SET([], multiple=True)
            w_out = widget(dummy_field, level_values, **w_attr)

            script = s3.jquery_ready[0] if s3.jquery_ready else ""
            s3.jquery_ready = jquery_ready
            script = f"S3.{name.replace('-', '_')}=function(){{{script}}}"
            s3.js_global.append(script)
            return w_out

    @property
    def levels(self):
        if self._levels is None:
            opts = self.opts
            hierarchy = current.gis.get_location_hierarchy()
            if "levels" in opts:
                self._levels = OrderedDict((l, hierarchy.get(l, l)) for l in opts.levels)
            else:
                self._levels = current.gis.get_relevant_hierarchy_levels(as_dict=True)

            for level in self._levels:
                self._levels[level] = {
                    "label": self._levels[level],
                    "options": {} if self.translate else []
                }
        return self._levels

    def _options(self, resource, values=None, inject_hierarchy=True):
        s3db = current.s3db
        opts, ftype = self.opts, "reference gis_location"
        levels = self.levels
        no_opts = opts.get("no_opts") or current.T("No options available")
        
        selector = self.field if resource else opts.get("lookup", "location_id")
        if not resource and opts.get("resource"):
            resource = s3db.resource(opts.resource)

        filters_added = False
        fixed_options = opts.get("options")

        if fixed_options:
            resource = s3db.resource("gis_location", id=fixed_options)
        elif selector and resource:
            rfield = S3ResourceField(resource, selector)
            if not rfield.field or rfield.ftype != ftype:
                raise TypeError(f"Invalid selector: {selector}")
            resource.add_filter(FS(selector) != None)
            resource.add_filter(FS(f"{selector}$end_date") == None)
            filters_added = True
        else:
            return (ftype, levels, no_opts)

        rows = self._lookup_options(levels, resource, selector, fixed_options, self.translate)

        if filters_added:
            resource.rfilter.filters.pop()
            resource.rfilter.filters.pop()
            resource.rfilter.query = resource.rfilter.transformed = None

        if values:
            rows = self._add_selected(rows, values, levels, self.translate)

        if not rows:
            return (ftype, levels, no_opts)

        local_names = self._get_local_names(rows) if self.translate else {}

        toplevel = list(levels.keys())[0]
        hierarchy_tree = {toplevel: {}}
        for row in rows:
            h = hierarchy_tree[toplevel]
            for level in levels:
                name = row.get(level)
                if not name: continue
                opts_level = levels[level]["options"]
                if name not in opts_level:
                    if self.translate:
                        opts_level[name] = local_names.get(name, name)
                    else:
                        opts_level.append(name)
                if inject_hierarchy:
                    if name not in h: h[name] = {}
                    h = h[name]

        self._sort_options(levels, translate=self.translate)

        if inject_hierarchy:
            js_global = current.response.s3.js_global
            jsons = lambda v: json.dumps(v, separators=JSONSEPARATORS)
            js_global.append(f"S3.location_filter_hierarchy={jsons(hierarchy_tree)}")
            if self.translate:
                js_global.append(f"S3.location_name_l10n={jsons(local_names)}")

        return (ftype, levels, None)

    def _lookup_options(self, levels, resource, selector, location_ids, path):
        db, s3db = current.db, current.s3db
        ltable = s3db.gis_location
        
        if location_ids:
            location_ids = set(location_ids)
            query, join = ltable.id.belongs(location_ids), None
        else:
            location_ids = set()
            rfield = resource.resolve_selector(selector)
            from ..resource import S3Joins
            joins = S3Joins(resource.tablename)
            joins.extend(rfield._joins)
            join = joins.as_list()
            join.append(ltable.on(ltable.id == rfield.field))
            query = resource.get_query()

        fields = [ltable.id, ltable.parent, ltable.level] + [ltable[lvl] for lvl in levels]
        if path: fields.append(ltable.path)

        rname = db._referee_name
        db._referee_name = None
        
        results = None
        level_keys = set(levels.keys())

        while True:
            if location_ids:
                query = ltable.id.belongs(location_ids)
                join = None
            relevant_query = ltable.level.belongs(level_keys) if path else (ltable.level != None)
            lx_rows = db(query & relevant_query).select(join=join, groupby=ltable.id, *fields)
            if lx_rows:
                results = (results | lx_rows) if results else lx_rows
            parents = db(query & (ltable.parent != None)).select(ltable.parent, join=join, groupby=ltable.parent)
            location_ids = set(row.parent for row in parents if row.parent)
            if not location_ids: break

        db._referee_name = rname
        return results

    def _get_local_names(self, rows):
        local_names = {}
        ids = set()
        for row in rows:
            p = row.get("path")
            if p: ids |= set(p.split("/"))
        if ids:
            s3db = current.s3db
            ltable, ntable = s3db.gis_location, s3db.gis_location_name
            query = (ltable.id.belongs(ids)) & (ntable.deleted == False) & \
                    (ntable.location_id == ltable.id) & \
                    (ntable.language == current.session.s3.language)
            nrows = current.db(query).select(ltable.name, ntable.name_l10n)
            for row in nrows:
                local_names[row.gis_location.name] = row.gis_location_name.name_l10n
        return local_names

    def _add_selected(self, rows, values, levels, translate):
        db, s3db = current.db, current.s3db
        ltable = s3db.gis_location
        accessible = current.auth.s3_accessible_query("read", ltable)
        fields = [ltable.id] + [ltable[l] for l in levels]
        if translate: fields.append(ltable.path)

        for f, v in values.items():
            if not v: continue
            level = f"L{f.split('L', 1)[1][0]}"
            query = accessible & (ltable.level == level) & (ltable.name.belongs(v)) & (ltable.end_date == None)
            selected = db(query).select(*fields)
            rows = (rows | selected) if rows else selected
        return rows

    def _sort_options(self, levels, translate=False):
        for level in levels:
            opts = levels[level]["options"]
            if translate:
                levels[level]["options"] = OrderedDict(sorted(opts.items()))
            else:
                opts.sort()

# =============================================================================
class MapFilter(FilterWidget):
    """
    Map filter widget for spatial queries.
    """

    css_base = "map-filter"
    operator = "intersects"

    def widget(self, resource, values):
        settings = current.deployment_settings
        if not settings.get_gis_spatialdb():
            current.log.warning("No Spatial DB => Disabling MapFilter")
            return ""

        attr = self._attr(resource)
        opts_get = self.opts.get
        css = attr.get("class")
        _class = f"{css} {self.css_base}" if css else self.css_base
        _id = attr.get("_id")

        hidden_input = INPUT(_type="hidden", _class=_class, _id=_id)
        if values:
            if isinstance(values, list):
                values = values[0]
            hidden_input["_value"] = values

        map_id = f"{_id}-map"
        c, f = resource.tablename.split("_", 1)
        c, f = opts_get("controller", c), opts_get("function", f)

        ltable = current.s3db.gis_layer_feature
        query = (ltable.controller == c) & (ltable.function == f) & (ltable.deleted == False)
        layer = current.db(query).select(ltable.layer_id, ltable.name, limitby=(0, 1)).first()

        layer_id = layer.layer_id if layer else None
        layer_name = layer.name if layer else resource.tablename

        feature_resources = [{
            "name": current.T(layer_name),
            "id": "search_results",
            "layer_id": layer_id,
            "filter": opts_get("filter"),
        }]

        button = opts_get("button")
        _map = current.gis.show_map(
            id=map_id,
            height=opts_get("height", settings.get_gis_map_height()),
            width=opts_get("width", settings.get_gis_map_width()),
            collapsed=True,
            callback=f"S3.search.s3map('{map_id}')",
            feature_resources=feature_resources,
            toolbar=not bool(button),
            add_polygon=True,
        )

        return TAG[""](hidden_input, button, _map)