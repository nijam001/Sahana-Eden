"""
    Assets Model
    Copyright: 2009-2022 (c) Sahana Software Foundation
    License: MIT
"""

__all__ = ("AssetModel",
           "AssetHRModel",
           "AssetTeamModel",
           "AssetTelephoneModel",
           "asset_types",
           "asset_log_status",
           "asset_controller",
           "asset_AssetRepresent",
           )

import json
from gluon import *
from gluon.storage import Storage
from ..core import *

# Asset Types
ASSET_TYPE_VEHICLE   = 1
ASSET_TYPE_TELEPHONE = 3
ASSET_TYPE_OTHER     = 4

asset_types = {"VEHICLE"   : ASSET_TYPE_VEHICLE,
               "TELEPHONE" : ASSET_TYPE_TELEPHONE,
               "OTHER"     : ASSET_TYPE_OTHER,
               }

# Asset Log Statuses
ASSET_LOG_SET_BASE = 1
ASSET_LOG_ASSIGN   = 2
ASSET_LOG_RETURN   = 3
ASSET_LOG_CHECK    = 4
ASSET_LOG_REPAIR   = 5
ASSET_LOG_DONATED  = 32
ASSET_LOG_LOST     = 33
ASSET_LOG_STOLEN   = 34
ASSET_LOG_DESTROY  = 35

asset_log_status = {"SET_BASE" : ASSET_LOG_SET_BASE,
                    "ASSIGN"   : ASSET_LOG_ASSIGN,
                    "RETURN"   : ASSET_LOG_RETURN,
                    "CHECK"    : ASSET_LOG_CHECK,
                    "REPAIR"   : ASSET_LOG_REPAIR,
                    "DONATED"  : ASSET_LOG_DONATED,
                    "LOST"     : ASSET_LOG_LOST,
                    "STOLEN"   : ASSET_LOG_STOLEN,
                    "DESTROY"  : ASSET_LOG_DESTROY,
                    }

# =============================================================================
class AssetModel(DataModel):
    """
        Asset Management
    """

    names = ("asset_asset",
             "asset_item",
             "asset_log",
             "asset_asset_id",
             )

    def model(self):

        T = current.T
        db = current.db
        auth = current.auth
        user = auth.user
        LOGGED_IN = auth.is_logged_in()
        s3 = current.response.s3

        item_id = self.supply_item_id
        item_entity_id = self.supply_item_entity_id
        location_id = self.gis_location_id
        organisation_id = self.org_organisation_id
        person_id = self.pr_person_id

        messages = current.messages
        NONE = messages["NONE"]
        UNKNOWN_OPT = messages.UNKNOWN_OPT
        YES = T("Yes")

        settings = current.deployment_settings
        org_site_label = settings.get_org_site_label()
        telephones = settings.get_asset_telephones()
        vehicles = settings.has_module("vehicle")
        types = telephones or vehicles

        # Shortcuts
        add_components = self.add_components
        configure = self.configure
        crud_strings = s3.crud_strings
        define_table = self.define_table
        super_link = self.super_link

        # Options
        asset_type_opts = {ASSET_TYPE_OTHER: T("Other")}
        if telephones:
            asset_type_opts[ASSET_TYPE_TELEPHONE] = T("Telephone")
        if vehicles:
            asset_type_opts[ASSET_TYPE_VEHICLE] = T("Vehicle")

        asset_condition_opts = {1: T("Good Condition"),
                                2: T("Minor Damage"),
                                3: T("Major Damage"),
                                4: T("Un-Repairable"),
                                5: T("Needs Maintenance"),
                                }

        ctable = self.supply_item_category
        itable = self.supply_item
        supply_item_represent = self.supply_item_represent
        asset_items_set = db((ctable.can_be_asset == True) & \
                             (itable.item_category_id == ctable.id))

        # ---------------------------------------------------------------------
        # Assets Table
        tablename = "asset_asset"
        define_table(tablename,
                     super_link("track_id", "sit_trackable"),
                     super_link("doc_id", "doc_entity"),
                     item_entity_id(),
                     Field("number", label=T("Asset Number")),
                     Field("type", "integer",
                           default=ASSET_TYPE_OTHER,
                           label=T("Type"),
                           represent=lambda opt: asset_type_opts.get(opt, UNKNOWN_OPT),
                           requires=IS_IN_SET(asset_type_opts),
                           readable=types, writable=types),
                     item_id(represent=supply_item_represent,
                             requires=IS_ONE_OF(asset_items_set, "supply_item.id",
                                                supply_item_represent, sort=True),
                             script=None, widget=None),
                     Field("kit", "boolean", default=False, label=T("Kit?"),
                           represent=lambda opt: YES if opt else NONE,
                           readable=False, writable=False),
                     organisation_id(default=user.organisation_id if LOGGED_IN else None,
                                     requires=self.org_organisation_requires(updateable=True),
                                     required=True,
                                     script='''$.filterOptionsS3({'trigger':'organisation_id','target':'site_id','lookupResource':'site','lookupPrefix':'org','lookupField':'site_id','lookupURL':S3.Ap.concat('/org/sites_for_org.json/')})'''),
                     super_link("site_id", "org_site",
                                default=user.site_id if LOGGED_IN else None,
                                empty=False, label=org_site_label, ondelete="RESTRICT",
                                represent=self.org_site_represent, readable=True, writable=True),
                     Field("sn", label=T("Serial Number")),
                     organisation_id("supply_org_id", label=T("Supplier/Donor"), ondelete="SET NULL"),
                     DateField("purchase_date", label=T("Purchase Date")),
                     Field("purchase_price", "double", label=T("Purchase Price"),
                           represent=lambda v, r=None: IS_FLOAT_AMOUNT.represent(v, precision=2)),
                     CurrencyField("purchase_currency"),
                     location_id(readable=False, writable=False),
                     person_id("assigned_to_id", readable=False, writable=False),
                     Field("cond", "integer", label=T("Condition"),
                           represent=lambda opt: asset_condition_opts.get(opt, UNKNOWN_OPT),
                           writable=False),
                     CommentsField(),
                     )

        crud_strings[tablename] = Storage(
            label_create=T("Create Asset"),
            title_display=T("Asset Details"),
            title_list=T("Assets"),
            title_update=T("Edit Asset"),
            title_upload=T("Import Assets"),
            label_list_button=T("List Assets"),
            label_delete_button=T("Delete Asset"),
            msg_record_created=T("Asset added"),
            msg_record_modified=T("Asset updated"),
            msg_record_deleted=T("Asset deleted"),
            msg_list_empty=T("No Assets currently registered"))

        asset_represent = asset_AssetRepresent(show_link=True)

        asset_id = FieldTemplate("asset_id", f"reference {tablename}",
                                 label=T("Asset"), ondelete="CASCADE",
                                 represent=asset_represent,
                                 requires=IS_EMPTY_OR(IS_ONE_OF(db, "asset_asset.id", asset_represent, sort=True)),
                                 sortby="number")

        # Configuration for Filters and Reports
        levels = current.gis.get_relevant_hierarchy_levels()
        list_fields = ["id", "item_id$item_category_id", "item_id", "number", 
                       (T("Assigned To"), "assigned_to_id"), "organisation_id", "site_id"]
        
        report_fields = ["number", (T("Category"), "item_id$item_category_id"), 
                         (T("Item"), "item_id"), "organisation_id", "site_id", "cond"]

        text_fields = ["number", "item_id$name", "comments"]

        for level in levels:
            lfield = f"location_id${level}"
            report_fields.append(lfield)
            text_fields.append(lfield)
            list_fields.append(lfield)

        list_fields.extend(("cond", "comments"))

        # Filter Widgets
        if settings.get_org_branches():
            org_filter = HierarchyFilter("organisation_id", hidden=True, leafonly=False)
        else:
            org_filter = OptionsFilter("organisation_id", search=True, header="", hidden=True)

        filter_widgets = [
            TextFilter(text_fields, label=T("Search"), 
                       comment=T("Search by asset number, item description or comments.")),
            OptionsFilter("item_id$item_category_id"),
            org_filter,
            LocationFilter("location_id", levels=levels, hidden=True),
            OptionsFilter("cond", hidden=True),
        ]

        configure(tablename,
                  context={"incident": "incident.id", "location": "location_id", "organisation": "organisation_id"},
                  create_next=URL(c="asset", f="asset", args=["[id]"]),
                  deduplicate=S3Duplicate(primary=("number",), secondary=("site_id", "organisation_id")),
                  filter_widgets=filter_widgets,
                  list_fields=list_fields,
                  onaccept=self.asset_onaccept,
                  summary=[{"name": "addform", "common": True, "widgets": [{"method": "create"}]},
                           {"name": "table", "label": "Table", "widgets": [{"method": "datatable"}]},
                           {"name": "report", "label": "Report", "widgets": [{"method": "report", "ajax_init": True}]}],
                  super_entity=("supply_item_entity", "sit_trackable"))

        add_components(tablename, asset_log="asset_id", asset_item="asset_id", asset_telephone="asset_id")

        # ---------------------------------------------------------------------
        # Asset Log Table
        asset_log_status_opts = {ASSET_LOG_SET_BASE: T("Base %(facility)s Set") % {"facility": org_site_label},
                                 ASSET_LOG_ASSIGN: T("Assigned"),
                                 ASSET_LOG_RETURN: T("Returned"),
                                 ASSET_LOG_CHECK: T("Checked"),
                                 ASSET_LOG_REPAIR: T("Repaired"),
                                 ASSET_LOG_DONATED: T("Donated"),
                                 ASSET_LOG_LOST: T("Lost"),
                                 ASSET_LOG_STOLEN: T("Stolen"),
                                 ASSET_LOG_DESTROY: T("Destroyed")}

        tablename = "asset_log"
        define_table(tablename,
                     asset_id(),
                     Field("status", "integer", label=T("Status"),
                           represent=lambda opt: asset_log_status_opts.get(opt, UNKNOWN_OPT),
                           requires=IS_IN_SET(asset_log_status_opts)),
                     DateTimeField("datetime", default="now", empty=False, represent="date"),
                     DateTimeField("datetime_until", label=T("Date Until"), represent="date"),
                     person_id(label=T("Assigned To")),
                     organisation_id(readable=False, writable=False),
                     super_link("site_id", "org_site", label=org_site_label,
                                instance_types=auth.org_site_types, represent=self.org_site_represent),
                     self.org_room_id(),
                     Field("cancel", "boolean", default=False, label=T("Cancel Log Entry")),
                     Field("cond", "integer", label=T("Condition"),
                           represent=lambda opt: asset_condition_opts.get(opt, UNKNOWN_OPT),
                           requires=IS_IN_SET(asset_condition_opts, zero=f"{T('Please select')}...")),
                     person_id("by_person_id", default=auth.s3_logged_in_person(), label=T("Assigned By")),
                     CommentsField())

        configure(tablename, onaccept=self.asset_log_onaccept, orderby="asset_log.datetime desc")

        return {"asset_asset_id": asset_id, "asset_represent": asset_represent}

    @staticmethod
    def asset_onaccept(form):
        """ Update Base Location and Kit components """
        if current.response.s3.bulk:
            return

        db = current.db
        atable = db.asset_asset
        asset_id = form.vars.get("id")
        
        record = db(atable.id == asset_id).select(atable.organisation_id, atable.site_id, atable.kit, limitby=(0, 1)).first()
        if record and record.site_id:
            stable = db.org_site
            site = db(stable.site_id == record.site_id).select(stable.location_id, limitby=(0, 1)).first()
            if site:
                tracker = S3Tracker()(atable, asset_id)
                tracker.set_base_location(site.location_id)
                
                db.asset_log.insert(asset_id=asset_id, status=ASSET_LOG_SET_BASE,
                                    organisation_id=record.organisation_id,
                                    site_id=record.site_id, cond=1)

    @staticmethod
    def asset_log_onaccept(form):
        """ Sync Asset Condition and Tracker status """
        db = current.db
        form_vars = form.vars
        asset_id = db.asset_log[form_vars.id].asset_id
        
        # Update main asset condition
        db(db.asset_asset.id == asset_id).update(cond=form_vars.cond)

# =============================================================================
class asset_AssetRepresent(S3Represent):
    """ Modernized Representation of Assets """

    def __init__(self, show_link=False, multiple=False):
        super().__init__(lookup="asset_asset", show_link=show_link, multiple=multiple)

    def lookup_rows(self, key, values, fields=None):
        db = current.db
        table = db.asset_asset
        itable = db.supply_item
        btable = db.supply_brand
        
        query = (table.id.belongs(values)) & (itable.id == table.item_id)
        return db(query).select(table.id, table.number, itable.name, btable.name,
                                left=btable.on(itable.brand_id == btable.id))

    def represent_row(self, row):
        number = row.get("asset_asset.number")
        item = row.get("supply_item.name")
        brand = row.get("supply_brand.name")

        if not number:
            return self.default
        
        res = f"{number} ({item}"
        return f"{res}, {brand})" if brand else f"{res})"

# =============================================================================
def asset_controller():
    """ RESTful CRUD controller """
    s3 = current.response.s3

    def prep(r):
        current.s3db.gis_location_filter(r)
        if r.component_name == "log":
            asset_log_prep(r)
        return True
    
    s3.prep = prep
    return current.crud_controller("asset", "asset", rheader=asset_rheader)

def asset_get_current_log(asset_id):
    table = current.s3db.asset_log
    query = (table.asset_id == asset_id) & (table.cancel == False) & (table.deleted == False)
    return current.db(query).select(orderby=~table.datetime, limitby=(0, 1)).first() or Storage()

def asset_rheader(r):
    if r.representation != "html" or not r.record:
        return None
    
    T = current.T
    record = r.record
    current_log = asset_get_current_log(record.id)
    
    tabs = [(T("Edit Details"), None), (T("Log"), "log"), (T("Documents"), "document")]
    rheader_tabs = sheader_tabs(r, tabs)
    
    return DIV(TABLE(TR(TH(f"{T('Number')}: "), record.number, 
                        TH(f"{T('Condition')}: "), current_log.get("cond", T("Unknown")))),
               rheader_tabs)