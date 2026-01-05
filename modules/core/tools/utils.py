"""
    Utilities

    Copyright: (c) 2010-2022 Sahana Software Foundation

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

__all__ = ("JSONSEPARATORS",
           "CustomController",
           "MarkupStripper",
           "StringTemplateParser",
           "Traceback",
           "FormKey",
           "URL2",
           "get_crud_string",
           "get_form_record_id",
           "get_form_record_data",
           "accessible_pe_query",
           "set_last_record_id",
           "get_last_record_id",
           "remove_last_record_id",
           "deduplicate_links",
           "s3_addrow",
           "s3_dev_toolbar",
           "s3_flatlist",
           "datahash",
           "s3_get_extension",
           "s3_get_extension_from_url",
           "s3_get_foreign_key",
           "s3_has_foreign_key",
           "s3_keep_messages",
           "s3_mark_required",
           "s3_orderby_fields",
           "s3_redirect_default",
           "s3_represent_value",
           "s3_required_label",
           "s3_set_extension",
           "s3_set_match_strings",
           "s3_strip_markup",
           "s3_validate",
           "system_info",
           "version_info",
           )

import copy
import os
import platform
import sys

from html.parser import HTMLParser
from urllib import parse as urlparse

from gluon import current, redirect, HTTP, URL, \
                  A, BEAUTIFY, CODE, DIV, PRE, SPAN, TABLE, TAG, TR, TD, \
                  IS_EMPTY_OR, IS_NOT_IN_DB
from gluon.tools import addrow

from s3dal import Expression, Field, Row, S3DAL

from .convert import s3_str

# Compact JSON encoding
JSONSEPARATORS = (",", ":")

# Session variable to store last record IDs
LAST_ID = "_last_record_id"

# =============================================================================
def get_crud_string(tablename, key):
    """
        Get a CRUD string (label) for a table

        Args:
            tablename: the table name
            key: the CRUD string key

        Returns:
            the CRUD string (usually lazyT)
    """

    crud_strings = current.response.s3.crud_strings

    labels = crud_strings.get(tablename)
    label = labels.get(key) if labels else None
    if label is None:
        label = crud_strings.get(key)

    return label

# =============================================================================
def get_form_record_id(form):
    """
        Returns the record ID from a FORM

        Args:
            form: the FORM

        Returns:
            the record ID, or None
    """

    form_vars = form.vars
    if "id" in form_vars:
        record_id = form_vars.id
    elif hasattr(form, "record_id"):
        record_id = form.record_id
    else:
        record_id = None

    return record_id

# =============================================================================
def get_form_record_data(form, table, fields):
    """
        Returns prospective record values for validation; looks up existing
        record values and table defaults if some fields are missing from the
        form.

        Args:
            form: the FORM (e.g. SQLFORM or custom FORM)
            table: the Table object the form is based on
            fields: list of field names to extract values for

        Returns:
            a dict {fieldname: value}, where each field is guaranteed to appear:
                - value from form.vars if present
                - otherwise value from the existing record (if record_id given)
                - otherwise the field default (if defined)
                - otherwise None
    """

    # Shorthand to access submitted values
    form_vars = form.vars

    # This will contain the final data for each field
    form_data = {}

    # Try to determine which record (if any) this form refers to
    record_id = get_form_record_id(form)

    # Fields which we need to look up from the existing record in the database
    lookup = []

    for fn in fields:
        if fn in form_vars:
            # If the form contains this field, use the submitted value
            form_data[fn] = form_vars[fn]
        elif record_id:
            # Field not in the form, but we know the record:
            # remember it so we can load it from the DB
            lookup.append(fn)
        else:
            # No record_id available: fall back to the table default
            form_data[fn] = table[fn].default

    if lookup and record_id:
        # Load the missing fields from the existing record in the DB
        db = current.db
        fields_to_select = [table[fn] for fn in lookup]

        row = db(table.id == record_id).select(*fields_to_select,
                                               limitby=(0, 1),
                                               ).first()
        if row:
            form_data.update({fn: row[fn] for fn in lookup})
        else:
            # Record not found: be explicit and set them to None
            form_data.update({fn: None for fn in lookup})
    else:
        # Nothing to look up (either no missing fields or no record_id)
        form_data.update({fn: None for fn in lookup})

    return form_data


# =============================================================================
def accessible_pe_query(table = None,
                        instance_types = None,
                        method = "update",
                        c = None,
                        f = None,
                        ):
    """
        Construct a query for accessible person entities (pe_ids),
        for pe_id-based filters and selectors

        Args:
            table: the table to query (default: pr_pentity)
            instance_types: the instance types to authorize
            method: the access method for which permission is required
            c: override current.request.controller for permission check
            f: override current.request.function for permission check

        Returns:
            the Query
    """

    if instance_types is None:
        instance_types = ("org_organisation",)

    db = current.db
    s3db = current.s3db

    if table is None:
        table = s3db.pr_pentity

    query = None
    accessible_query = current.auth.s3_accessible_query
    for instance_type in instance_types:

        itable = s3db.table(instance_type)
        if not itable:
            continue

        dbset = db(accessible_query(method, itable, c=c, f=f))._select(itable.pe_id)
        subquery = table.pe_id.belongs(dbset)
        query = subquery if query is None else (query | subquery)

    return query

# =============================================================================
def set_last_record_id(tablename, record_id):
    """
        Stores the ID of the last processed record of a table in the session

        Args:
            tablename: the tablename
            record_id: the record ID
    """

    try:
        record_id = int(record_id)
    except ValueError:
        return

    session_s3 = current.session.s3

    last_id = session_s3.get(LAST_ID)
    if last_id is None:
        session_s3[LAST_ID] = {tablename: record_id}
    else:
        last_id[tablename] = record_id

# -----------------------------------------------------------------------------
def get_last_record_id(tablename):
    """
        Reads the ID of the last processed record of a table from the session

        Args:
            tablename: the tablename
    """

    session_s3 = current.session.s3

    last_id = session_s3.get(LAST_ID)
    if last_id is not None:
        last_id = last_id.get(tablename)
    return last_id

# -----------------------------------------------------------------------------
def remove_last_record_id(tablename=None):
    """
        Removes the ID of the last processed record of a table from the session

        Args:
            tablename: the tablename

        Note:
            - if no tablename is specified, all last record IDs will be removed
    """

    session_s3 = current.session.s3

    last_id = session_s3.get(LAST_ID)
    if last_id is not None:
        if tablename:
            last_id.pop(tablename, None)
        else:
            del session_s3[LAST_ID]

# =============================================================================
def deduplicate_links(table, *fieldnames):
    """
        Removes any duplicates (by combination of specified fields) in a
        link table; useful to clean up after imports or merge

        Args:
            table: the target Table
            fieldnames: names of fields to de-duplicate by

        Returns:
            total number of deleted duplicates
    """

    db = current.db

    base_query = (table.deleted == False) if "deleted" in table else (table.id>0)

    total = table._id.count()
    original = table._id.min()

    fields = []
    query = base_query
    for fn in fieldnames:
        field = table[fn]
        fields.append(field)
        query = (field != None) & query
    rows = db(query).select(total,
                            original,
                            *fields,
                            groupby = fields,
                            having = total > 1,
                            )
    result = 0
    for row in rows:
        link = row[table]
        query = base_query & (table._id > row[original])
        for field in fields:
            query = (field == link[field]) & query
        result += db(query).delete()

    return result

# =============================================================================
def s3_validate(table, field, value, record=None):
    """
        Validates a value for a field

        Args:
            table: Table
            field: Field or name of the field
            value: value to validate
            record: the existing database record, if available

        Returns:
            tuple (value, error)
    """

    default = (value, None)

    if isinstance(field, str):
        fieldname = field
        if fieldname in table.fields:
            field = table[fieldname]
        else:
            return default
    else:
        fieldname = field.name

    self_id = None

    if record is not None:

        try:
            v = record[field]
        except: # KeyError is now AttributeError
            v = None
        if v and v == value:
            return default

        try:
            self_id = record[table._id]
        except: # KeyError is now AttributeError
            pass

    requires = field.requires

    if field.unique and not requires:
        # Prevent unique-constraint violations
        field.requires = IS_NOT_IN_DB(current.db, str(field))
        if self_id:
            field.requires.set_self_id(self_id)

    elif self_id:

        # Initialize all validators for self_id
        if not isinstance(requires, (list, tuple)):
            requires = [requires]
        for r in requires:
            if hasattr(r, "set_self_id"):
                r.set_self_id(self_id)
            if hasattr(r, "other") and \
               hasattr(r.other, "set_self_id"):
                r.other.set_self_id(self_id)

    try:
        value, error = field.validate(value)
    except:
        # Oops - something went wrong in the validator:
        # write out a debug message, and continue anyway
        current.log.error("Validate %s: %s (ignored)" %
                          (field, sys.exc_info()[1]))
        return (None, None)
    else:
        return (value, error)

# =============================================================================
def s3_represent_value(field,
                       value = None,
                       record = None,
                       linkto = None,
                       strip_markup = False,
                       xml_escape = False,
                       non_xml_output = False,
                       extended_comments = False
                       ):
    """
        Represent a field value

        Args:
            field: the field (Field)
            value: the value
            record: record to retrieve the value from
            linkto: function or format string to link an ID column
            strip_markup: strip away markup from representation
            xml_escape: XML-escape the output
            non_xml_output: Needed for output such as pdf or xls
            extended_comments: Typically the comments are abbreviated
    """

    xml_encode = current.xml.xml_encode

    NONE = current.response.s3.crud_labels["NONE"]
    cache = current.cache
    fname = field.name

    # Get the value
    if record is not None:
        tablename = str(field.table)
        if tablename in record and isinstance(record[tablename], Row):
            text = val = record[tablename][field.name]
        else:
            text = val = record[field.name]
    else:
        text = val = value

    ftype = str(field.type)
    if ftype[:5] == "list:" and not isinstance(val, list):
        # Default list representation can't handle single values
        val = [val]

    # Always XML-escape content markup if it is intended for xml output
    # This code is needed (for example) for a data table that includes a link
    # Such a table can be seen at inv/inv_item
    # where the table displays a link to the warehouse
    if not non_xml_output:
        if not xml_escape and val is not None:
            if ftype in ("string", "text"):
                val = text = xml_encode(s3_str(val))
            elif ftype == "list:string":
                val = text = [xml_encode(s3_str(v)) for v in val]

    # Get text representation
    if field.represent:
        try:
            key = s3_str("%s_repr_%s" % (field, val))
        except (UnicodeEncodeError, UnicodeDecodeError):
            text = field.represent(val)
        else:
            text = cache.ram(key,
                             lambda: field.represent(val),
                             time_expire = 60,
                             )
        if isinstance(text, DIV):
            text = str(text)
        elif not isinstance(text, str):
            text = s3_str(text)
    else:
        if val is None:
            text = s3_str(NONE)
        elif fname == "comments" and not extended_comments:
            ur = s3_str(text)
            if len(ur) > 48:
                text = s3_str("%s..." % ur[:45])
        else:
            text = s3_str(text)

    # Strip away markup from text
    if strip_markup and "<" in text:
        try:
            stripper = MarkupStripper()
            stripper.feed(text)
            text = stripper.stripped()
        except:
            pass

    # Link ID field
    if fname == "id" and linkto:
        link_id = str(val)
        try:
            href = linkto(link_id)
        except TypeError:
            href = linkto % link_id
        href = str(href).replace(".aadata", "")
        return A(text, _href=href).xml()

    # XML-escape text
    elif xml_escape:
        text = xml_encode(text)

    #try:
    #    text = text.decode("utf-8")
    #except:
    #    pass

    return text

# =============================================================================
def s3_dev_toolbar():
    """
        Developer Toolbar - ported from gluon.Response.toolbar()
        Shows useful stuff at the bottom of the page in Debug mode
    """

    from gluon.dal import DAL
    from gluon.utils import web2py_uuid

    #admin = URL("admin", "default", "design", extension="html",
    #            args=current.request.application)
    BUTTON = TAG.button

    dbstats = []
    dbtables = {}
    infos = DAL.get_instances()
    for k, v in infos.items():
        dbstats.append(TABLE(*[TR(PRE(row[0]), "%.2fms" %
                                      (row[1] * 1000))
                                       for row in v["dbstats"]]))
        dbtables[k] = {"defined": v["dbtables"]["defined"] or "[no defined tables]",
                       "lazy": v["dbtables"]["lazy"] or "[no lazy tables]",
                       }

    u = web2py_uuid()
    backtotop = A("Back to top", _href="#totop-%s" % u)
    # Convert lazy request.vars from property to Storage so they
    # will be displayed in the toolbar.
    request = copy.copy(current.request)
    request.update(vars=current.request.vars,
                   get_vars=current.request.get_vars,
                   post_vars=current.request.post_vars)

    # Filter out sensitive session details
    def no_sensitives(key):
        if key in ("hmac_key", "password") or \
           key[:8] == "_formkey" or \
           key[-4:] == "_key" or \
           key[-5:] == "token":
            return None
        return key

    return DIV(
        #BUTTON("design", _onclick="document.location='%s'" % admin),
        BUTTON("request",
               _onclick="$('#request-%s').slideToggle().removeClass('hide')" % u),
        #BUTTON("response",
        #       _onclick="$('#response-%s').slideToggle().removeClass('hide')" % u),
        BUTTON("session",
               _onclick="$('#session-%s').slideToggle().removeClass('hide')" % u),
        BUTTON("db tables",
               _onclick="$('#db-tables-%s').slideToggle().removeClass('hide')" % u),
        BUTTON("db stats",
               _onclick="$('#db-stats-%s').slideToggle().removeClass('hide')" % u),
        DIV(BEAUTIFY(request), backtotop,
            _class="hide", _id="request-%s" % u),
        #DIV(BEAUTIFY(current.response), backtotop,
        #    _class="hide", _id="response-%s" % u),
        DIV(BEAUTIFY(current.session, keyfilter=no_sensitives), backtotop,
            _class="hide", _id="session-%s" % u),
        DIV(BEAUTIFY(dbtables), backtotop,
            _class="hide", _id="db-tables-%s" % u),
        DIV(BEAUTIFY(dbstats), backtotop,
            _class="hide", _id="db-stats-%s" % u),
        _id="totop-%s" % u
    )

# =============================================================================
def s3_required_label(field_label):
    """ Default HTML for labels of required form fields """

    return TAG[""]("%s:" % field_label, SPAN(" *", _class="req"))

# =============================================================================
def s3_mark_required(fields,
                     mark_required=None,
                     label_html=None,
                     map_names=None):
    """
        Add asterisk to field label if a field is required.

        This inspects both:
            - the field properties (required/notnull)
            - and its validators (e.g. IS_EMPTY_OR, validators with mark_required)

        Args:
            fields: list of Fields (or a Table to iterate over)
            mark_required: list/tuple of field names which should always
                           be treated as required even if the validator
                           would normally allow empty input
            label_html: callback to render labels for required fields,
                        defaults to s3_required_label()
            map_names: optional mapping for alternative field names + labels,
                       used e.g. for inline components:
                       {field.name: (name_in_form, label_in_form)}

        Returns:
            (labels, has_required) where:
                labels: dict {fieldname: rendered label text}
                has_required: True if any field is required
    """

    if not mark_required:
        mark_required = ()

    if label_html is None:
        # Default HTML for required labels (adds " *")
        # @ToDo: DRY this setting with s3.ui.locationselector.js
        label_html = s3_required_label

    labels = {}

    # Flag to mark if the form contains at least one required field
    has_required = False

    for field in fields:

        # Support renaming fields in the form (e.g. inline components)
        if map_names:
            fname, flabel = map_names[field.name]
        else:
            fname, flabel = field.name, field.label

        if not flabel:
            # If there is no label at all, store empty string
            labels[fname] = ""
            continue

        if field.writable:

            validators = field.requires

            # Special-case: if the validator is IS_EMPTY_OR and the field
            # is not explicitly in mark_required, then we allow empty input
            # even for notnull fields (e.g. when we populate them onvalidation)
            if isinstance(validators, IS_EMPTY_OR) and field.name not in mark_required:
                labels[fname] = "%s:" % flabel
                continue
            else:
                # Initial guess: required if explicitly marked or notnull
                required = field.required or field.notnull or \
                           field.name in mark_required

            # If still not marked required, inspect validators more closely
            if not validators and not required:
                labels[fname] = "%s:" % flabel
                continue

            if not required:

                if not isinstance(validators, (list, tuple)):
                    validators = [validators]

                for v in validators:

                    # Some validators expose "options" or "zero" attributes
                    # which affect whether they require a non-empty value
                    if hasattr(v, "options"):
                        if hasattr(v, "zero") and v.zero is None:
                            # Zero is not allowed => behaves like required
                            continue

                    # Some validators explicitly define mark_required
                    if hasattr(v, "mark_required"):
                        if v.mark_required:
                            required = True
                            break
                        else:
                            continue

                    # Fallback: try validate an empty value, and infer
                    # requirement from whether it returns an error
                    try:
                        error = v("")[1]
                    except TypeError:
                        # Some validators take no arguments
                        pass
                    else:
                        if error:
                            required = True
                            break

            if required:
                has_required = True
                labels[fname] = label_html(flabel)
            else:
                labels[fname] = "%s:" % flabel

        else:
            # Field not writable: no need to mark as required
            labels[fname] = "%s:" % flabel

    return (labels, has_required)

# =============================================================================
def s3_addrow(form, label, widget, comment, formstyle, row_id, position=-1):
    """
        Add a row to a form, applying formstyle

        Args:
            form: the FORM
            label: the label
            widget: the widget
            comment: the comment
            formstyle: the formstyle
            row_id: the form row HTML id
            position: position where to insert the row
    """

    if callable(formstyle):
        row = formstyle(row_id, label, widget, comment)
        if isinstance(row, (tuple, list)):
            for subrow in row:
                form[0].insert(position, subrow)
                if position >= 0:
                    position += 1
        else:
            form[0].insert(position, row)
    else:
        addrow(form, label, widget, comment, formstyle, row_id,
               position = position)
    return

# =============================================================================
def s3_keep_messages():
    """
        Retain user messages from previous request - prevents the messages
        from being swallowed by overhanging Ajax requests or intermediate
        pages with mandatory redirection (see s3_redirect_default)
    """

    response = current.response
    session = current.session

    session.confirmation = response.confirmation
    session.error = response.error
    session.flash = response.flash
    session.information = response.information
    session.warning = response.warning

# =============================================================================
def s3_redirect_default(location="", how=303, client_side=False, headers=None):
    """
        Redirect preserving response messages, useful when redirecting from
        index() controllers.

        Args:
            location: the url where to redirect
            how: what HTTP status code to use when redirecting
            client_side: if set to True, it triggers a reload of
                         the entire page when the fragment has been
                         loaded as a component
            headers: response headers
    """

    s3_keep_messages()

    redirect(location,
             how = how,
             client_side = client_side,
             headers = headers,
             )

# =============================================================================
def s3_has_foreign_key(field, m2m=True):
    """
        Check whether a field contains a foreign key constraint

        Args:
            field: the field (Field instance)
            m2m: also detect many-to-many links

        Note:
            many-to-many references (list:reference) are not DB constraints,
            but pseudo-references implemented by the DAL. If you only want
            to find real foreign key constraints, then set m2m=False.
    """

    try:
        ftype = str(field.type)
    except:
        # Virtual Field
        return False

    if ftype[:9] == "reference" or \
       m2m and ftype[:14] == "list:reference" or \
       current.s3db.virtual_reference(field):
        return True

    return False

# =============================================================================
def s3_get_foreign_key(field, m2m=True):
    """
        Resolve a field type into the name of the referenced table,
        the referenced key and the reference type (M:1 or M:N)

        Args:
            field: the field (Field instance)
            m2m: also detect many-to-many references

        Returns:
            tuple (tablename, key, multiple), where tablename is
            the name of the referenced table (or None if this field
            has no foreign key constraint), key is the field name of
            the referenced key, and multiple indicates whether this is
            a many-to-many reference (list:reference) or not.

        Note:
            many-to-many references (list:reference) are not DB constraints,
            but pseudo-references implemented by the DAL. If you only want
            to find real foreign key constraints, then set m2m=False.
    """

    ftype = str(field.type)
    multiple = False
    if ftype[:9] == "reference":
        key = ftype[10:]
    elif m2m and ftype[:14] == "list:reference":
        key = ftype[15:]
        multiple = True
    else:
        key = current.s3db.virtual_reference(field)
        if not key:
            return (None, None, None)
    if "." in key:
        rtablename, key = key.split(".")
    else:
        rtablename = key
        rtable = current.s3db.table(rtablename)
        if rtable:
            key = rtable._id.name
        else:
            key = None
    return (rtablename, key, multiple)

# =============================================================================
def s3_flatlist(nested):
    """ Iterator to flatten mixed iterables of arbitrary depth """

    import collections.abc

    for item in nested:
        if isinstance(item, collections.abc.Iterable) and \
           not isinstance(item, str):
            for sub in s3_flatlist(item):
                yield sub
        else:
            yield item

# =============================================================================
def datahash(*values):
    """
        Produce a data verification hash from the values

        Args:
            values: an (ordered) iterable of values

        Returns:
            the verification hash as string
    """

    import hashlib
    dstr = "|%s|" % "|".join([str(v) for v in values])

    return hashlib.sha512(dstr.encode("utf-8")).hexdigest().lower()

# =============================================================================
def s3_set_match_strings(matchDict, value):
    """
        Helper method for gis_search_ac and org_search_ac
        Find which field the search term matched & where

        Args:
            matchDict: usually the record
            value: the search term
    """

    for key in matchDict:
        v = matchDict[key]
        if not isinstance(v, str):
            continue
        l = len(value)
        if v[:l].lower() == value:
            # Match needs to start from beginning
            matchDict["match_type"] = key
            matchDict["match_string"] = v[:l] # Maintain original case
            next_string = v[l:]
            if next_string:
                matchDict["next_string"] = next_string
            break
        elif key == "addr" and value in v.lower():
            # Match can start after the beginning (to allow for house number)
            matchDict["match_type"] = key
            pre_string, next_string = v.lower().split(value, 1)
            if pre_string:
                matchDict["pre_string"] = v[:len(pre_string)] # Maintain original case
            if next_string:
                matchDict["next_string"] = v[(len(pre_string) + l):] # Maintain original case
            matchDict["match_string"] = v[len(pre_string):][:l] # Maintain original case
            break

# =============================================================================
def s3_orderby_fields(table, orderby, expr=False):
    """
        Introspect and yield all fields involved in a DAL orderby
        expression.

        Args:
            table: the Table
            orderby: the orderby expression
            expr: True to yield asc/desc expressions as they are,
                  False to yield only Fields
    """

    if not orderby:
        return

    adapter = S3DAL()
    COMMA = adapter.COMMA
    INVERT = adapter.INVERT

    if isinstance(orderby, str):
        items = orderby.split(",")
    elif type(orderby) is Expression:
        def expand(e):
            if isinstance(e, Field):
                return [e]
            if e.op == COMMA:
                return expand(e.first) + expand(e.second)
            elif e.op == INVERT:
                return [e] if expr else [e.first]
            return []
        items = expand(orderby)
    elif not isinstance(orderby, (list, tuple)):
        items = [orderby]
    else:
        items = orderby

    s3db = current.s3db
    tablename = table._tablename if table else None
    for item in items:
        if type(item) is Expression:
            if not isinstance(item.first, Field):
                continue
            f = item if expr else item.first
        elif isinstance(item, Field):
            f = item
        elif isinstance(item, str):
            fn, direction = (item.strip().split() + ["asc"])[:2]
            tn, fn = ([tablename] + fn.split(".", 1))[-2:]
            if tn:
                try:
                    f = s3db.table(tn, db_only=True)[fn]
                except (AttributeError, KeyError):
                    continue
            else:
                if current.response.s3.debug:
                    raise SyntaxError('Tablename prefix required for orderby="%s"' % item)
                else:
                    # Ignore
                    continue
            if expr and direction[:3] == "des":
                f = ~f
        else:
            continue
        yield f

# =============================================================================
def s3_get_extension(request=None):
    """
        Get the file extension in the path of the request

        Args:
            request: the request object (web2py request or CRUDRequest),
                     defaults to current.request
    """


    if request is None:
        request = current.request

    extension = request.extension
    if request.function == "ticket" and request.controller == "admin":
        extension = "html"
    elif "format" in request.get_vars:
        ext = request.get_vars.format
        if isinstance(ext, list):
            ext = ext[-1]
        extension = ext.lower() or extension
    else:
        ext = None
        for arg in request.args[::-1]:
            if "." in arg:
                ext = arg.rsplit(".", 1)[1].lower()
                break
        if ext:
            extension = ext
    return extension

# =============================================================================
def s3_get_extension_from_url(url):
    """
        Helper to read the format extension from a URL string

        Args:
            url: the URL string

        Returns:
            the format extension as string, if any
    """

    ext = None
    if not url:
        return ext

    try:
        parsed = urlparse.urlparse(url)
    except (ValueError, AttributeError):
        pass
    else:
        if parsed.query:
            params = parsed.query.split(",")
            for param in params[::-1]:
                k, v = param.split("=") if "=" in param else None, None
                if k == "format":
                    ext = v.lower()
                    break
        if not ext:
            args = parsed.path.split("/")
            for arg in args[::-1]:
                if "." in arg:
                    ext = arg.rsplit(".", 1)[-1]
                    break

    return ext

# =============================================================================
def s3_set_extension(url, extension=None):
    """
        Add a file extension to the path of a url, replacing all
        other extensions in the path.

        Args:
            url: the URL (as string)
            extension: the extension, defaults to the extension
                       of current. request
    """

    if extension == None:
        extension = s3_get_extension()
    #if extension == "html":
        #extension = ""

    u = urlparse.urlparse(url)

    path = u.path
    if path:
        if "." in path:
            elements = [p.split(".")[0] for p in path.split("/")]
        else:
            elements = path.split("/")
        if extension and elements[-1]:
            elements[-1] += ".%s" % extension
        path = "/".join(elements)
    return urlparse.urlunparse((u.scheme,
                                u.netloc,
                                path,
                                u.params,
                                u.query,
                                u.fragment))

# =============================================================================
class Traceback:
    """ Generate the traceback for viewing error Tickets """

    def __init__(self, text):
        """ Traceback constructor """

        self.text = text

    # -------------------------------------------------------------------------
    def xml(self):
        """ Returns the xml """

        output = self.make_links(CODE(self.text).xml())
        return output

    # -------------------------------------------------------------------------
    def make_link(self, path):
        """ Create a link from a path """

        tryFile = path.replace("\\", "/")

        if os.path.isabs(tryFile) and os.path.isfile(tryFile):
            folder, filename = os.path.split(tryFile)
            ext = os.path.splitext(filename)[1]
            app = current.request.args[0]

            editable = {"controllers": ".py", "models": ".py", "views": ".html"}
            l_ext = ext.lower()
            f_endswith = folder.endswith
            for key in editable.keys():
                check_extension = f_endswith("%s/%s" % (app, key))
                if l_ext == editable[key] and check_extension:
                    edit_url = URL(a = "admin",
                                   c = "default",
                                   f = "edit",
                                   args = [app, key, filename],
                                   )
                    return A('"' + tryFile + '"',
                             _href = edit_url,
                             _target = "_blank",
                             ).xml()
        return ""

    # -------------------------------------------------------------------------
    def make_links(self, traceback):
        """ Make links using the given traceback """

        lwords = traceback.split('"')

        # Make the short circuit compatible with <= python2.4
        result = lwords[0] if len(lwords) else ""

        i = 1

        while i < len(lwords):
            link = self.make_link(lwords[i])

            if link == "":
                result += '"' + lwords[i]
            else:
                result += s3_str(link)

                if i + 1 < len(lwords):
                    result += lwords[i + 1]
                    i = i + 1

            i = i + 1

        return result

# =============================================================================
def URL2(a=None, c=None, r=None):
    """
        Modified version of URL from gluon/html.py
            - used by views/layout_iframe.html for our jquery function

        @example:

        >>> URL(a="a",c="c")
        "/a/c"

        generates a url "/a/c" corresponding to application a & controller c
        If r=request is passed, a & c are set, respectively,
        to r.application, r.controller

        The more typical usage is:

        URL(r=request) that generates a base url with the present
        application and controller.

        The function (& optionally args/vars) are expected to be added
        via jquery based on attributes of the item.
    """

    application = controller = None
    if r:
        application = r.application
        controller = r.controller
    if a:
        application = a
    if c:
        controller = c
    if not (application and controller):
        raise SyntaxError("not enough information to build the url")
    #other = ""
    url = "/%s/%s" % (application, controller)
    return url

# =============================================================================
class CustomController:
    """
        Common helpers for custom controllers (template/controllers.py)

        TODO Add Helper Function for dataTables
        TODO Add Helper Function for dataLists
    """

    @staticmethod
    def _view(template, filename):
        """
            Use a custom view template

            Args:
                template: name of the template (determines the path)
                filename: name of the view template file
        """

        if "." in template:
            template = os.path.join(*(template.split(".")))

        view = os.path.join(current.request.folder, "modules", "templates",
                            template, "views", filename)

        try:
            # Pass view as file not str to work in compiled mode
            current.response.view = open(view, "rb")
        except IOError:
            msg = "Unable to open Custom View: %s" % view
            current.log.error("%s (%s)" % (msg, sys.exc_info()[1]))
            raise HTTP(404, msg)

# =============================================================================
class StringTemplateParser:
    """
        Helper to parse string templates with named keys
    """

    def __init__(self):
        self._keys = []

    def __getitem__(self, key):
        self._keys.append(key)

    @classmethod
    def keys(cls, template):
        """
            Get the keys from a string template

            Returns:
                a list of keys (in order of appearance),
                None for invalid string templates

            Example:
                keys = StringTemplateParser.keys("%(first_name)s %(last_name)s")
                # Returns: ["first_name", "last_name"]
        """

        parser = cls()
        try:
            template % parser
        except TypeError:
            return None
        return parser._keys

# =============================================================================
class MarkupStripper(HTMLParser):
    """ Simple markup stripper """

    def __init__(self):
        super().__init__()
        #self.reset() # Included in super-init
        self.result = []

    def handle_data(self, d):
        self.result.append(d)

    def stripped(self):
        return "".join(self.result)

def s3_strip_markup(text):

    try:
        stripper = MarkupStripper()
        stripper.feed(text)
        text = stripper.stripped()
    except Exception:
        pass
    return text

# =============================================================================
class FormKey:
    """
        Tool to facilitate XSRF protection for custom forms.

        Typical usage:

            formkey = FormKey("my_table/update/%s" % record_id).generate()
            form.hidden = {"_formkey": formkey}

        and on POST:

            formkey = FormKey("my_table/update/%s" % record_id)
            if not formkey.verify(request.post_vars):
                raise HTTP(403)

        Notes:
            - "formname" should uniquely describe both the action
              and (ideally) the target record to avoid collisions.
            - Up to 10 concurrent tokens are stored per formname;
              older ones are discarded.
            - By default, a form key can only be used once. This can be
              changed with the "invalidate" parameter of verify().
    """

    def __init__(self, formname):
        """
            Args:
                formname: name of the form/action that is being protected,
                          e.g. "my_table/update/4"
        """

        self.formname = formname

    # -------------------------------------------------------------------------
    def generate(self):
        """
            Generates a new form key and stores it in the current session.

            Returns:
                the form key as a hex string

            The key should be embedded in the response (e.g. hidden
            form field) and submitted again with the POST request.
        """

        from uuid import uuid4

        formkey = uuid4().hex
        keyname = "_formkey[%s]" % self.formname

        session = current.session
        # Only keep the last 9 keys, then add this one (max 10 total)
        session[keyname] = session.get(keyname, [])[-9:] + [formkey]

        return formkey

    # -------------------------------------------------------------------------
    def verify(self, post_vars, variable="_formkey", invalidate=True):
        """
            Verify the form key returned by the client.

            Args:
                post_vars: Storage/dict containing the POST variables
                variable: the field name that carries the form key
                invalidate: if True (default), consume the key on success,
                            so that it cannot be reused

            Returns:
                True if the key is valid, False otherwise
        """

        formkey = post_vars.get(variable)
        keyname = "_formkey[%s]" % self.formname

        keys = current.session.get(keyname, [])
        if not formkey or formkey not in keys:
            return False

        if invalidate:
            # Remove the key so it cannot be reused (prevents replay)
            keys.remove(formkey)

        return True


# =============================================================================
def system_info():
    """
        System Information, for issue reporting and support; visible e.g. on
        the default/about page

        Returns:
            a DIV with the system information
    """

    request = current.request
    settings = current.deployment_settings

    INCORRECT = "Not installed or incorrectly configured."
    UNKNOWN = "?"

    subheader = lambda title: TR(TD(title, _colspan="2"), _class="about-subheader")
    item = lambda title, value: TR(TD(title), TD(value))

    # Technical Support Details
    system_info = DIV(_class="system-info")

    # Application version
    try:
        with open(os.path.join(request.folder, "VERSION"), "r") as version_file:
            app_version = version_file.read().strip("\n")
    except IOError:
        app_version = UNKNOWN
    template = settings.get_template()
    if isinstance(template, (tuple, list)):
        template = ", ".join(template)
    trows = [subheader(settings.get_system_name_short()),
             item("Template", template),
             item("Version", app_version),
             ]

    # Server Components
    base_version = ".".join(map(str, version_info()))
    try:
        with open(os.path.join(request.env.web2py_path, "VERSION"), "r") as version_file:
            web2py_version = version_file.read()[8:].strip("\n")
    except IOError:
        web2py_version = UNKNOWN
    os_version = platform.platform()

    trows.extend([subheader("Server"),
                  item("Eden", base_version),
                  item("Web2Py", web2py_version),
                  item("HTTP Server", request.env.server_software),
                  item("Operating System", os_version),
                  ])

    # Database
    db_info = [subheader("Database")]

    dbtype = settings.get_database_type()
    if dbtype == "sqlite":
        try:
            import sqlite3
            sqlite_version = sqlite3.version
        except (ImportError, AttributeError):
            sqlite_version = UNKNOWN

        db_info.extend([item("SQLite", sqlite_version),
                        ])

    elif dbtype == "mysql":
        database_name = settings.database.get("database", "sahana")
        try:
            # @ToDo: Support using pymysql & Warn
            import MySQLdb
            mysqldb_version = MySQLdb.__revision__
        except (ImportError, AttributeError):
            mysqldb_version = INCORRECT
            mysql_version = UNKNOWN
        else:
            #mysql_version = (subprocess.Popen(["mysql", "--version"], stdout=subprocess.PIPE).communicate()[0]).rstrip()[10:]
            con = MySQLdb.connect(host = settings.database.get("host", "localhost"),
                                  port = settings.database.get("port", None) or 3306,
                                  db = database_name,
                                  user = settings.database.get("username", "sahana"),
                                  passwd = settings.database.get("password", "password")
                                  )
            cur = con.cursor()
            cur.execute("SELECT VERSION()")
            mysql_version = cur.fetchone()

        db_info.extend([item("MySQL", mysql_version),
                        item("MySQLdb python driver", mysqldb_version),
                        ])

    else:
        # Postgres
        try:
            import psycopg2
            psycopg_version = psycopg2.__version__
        except (ImportError, AttributeError):
            psycopg_version = INCORRECT
            pgsql_version = UNKNOWN
        else:
            con = psycopg2.connect(host = settings.db_params.get("host", "localhost"),
                                   port = settings.db_params.get("port", None) or 5432,
                                   database = settings.db_params.get("database", "eden"),
                                   user = settings.db_params.get("username", "eden"),
                                   password = settings.db_params.get("password", "password")
                                   )
            cur = con.cursor()
            cur.execute("SELECT version()")
            pgsql_version = cur.fetchone()

        db_info.extend([item("PostgreSQL", pgsql_version),
                        item("psycopg2 python driver", psycopg_version),
                        ])

    trows.extend(db_info)

    # Python and Libraries
    python_version = platform.python_version()
    #try:
    #    from lxml import etree
    #    lxml_version = ".".join([str(i) for i in etree.LXML_VERSION])
    #except (ImportError, AttributeError):
    #    lxml_version = INCORRECT
    #try:
    #    import reportlab
    #    reportlab_version = reportlab.Version
    #except (ImportError, AttributeError):
    #    reportlab_version = INCORRECT
    #try:
    #    import shapely
    #    shapely_version = shapely.__version__
    #except (ImportError, AttributeError):
    #    shapely_version = INCORRECT

    trows.extend([subheader("Python"),
                  item("Python", python_version),
                  #item("lxml", lxml_version),
                  #item("ReportLab", reportlab_version),
                  #item("Shapely", shapely_version),
                  ])

    system_info.append(TABLE(*trows))

    return system_info

# =============================================================================
def version_info():
    """
        Base system version info

        Returns:
            tuple: the base system version number as integer tuple
    """

    from ...._version import __version__

    return tuple(map(int, __version__.split(".")))

# END =========================================================================
