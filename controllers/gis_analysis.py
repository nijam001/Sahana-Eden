# This is a simplified file to help the Call Graph extension work.
# The original gis.py is too complex for the extension to parse correctly.
#
# INSTRUCTIONS:
# 1. Open this file in VS Code.
# 2. Click on the function name "ldata" below.
# 3. Press Ctrl+Shift+P -> "CallGraph.showOutgoingCallGraph"

import json

# Mocks to satisfy the static analyzer
class MockObject:
    def __getattr__(self, name):
        return MockObject()
    def __call__(self, *args, **kwargs):
        return MockObject()

request = MockObject()
response = MockObject()
session = MockObject()
settings = MockObject()
s3db = MockObject()
s3base = MockObject()
db = MockObject()
T = MockObject()
HTTP = MockObject()

# Copied ldata function
def ldata():
    """
        Return JSON of location hierarchy suitable for use by LocationSelector:
            GET '/eden/gis/ldata/' + id
    """

    req_args = request.args
    try:
        location_id = req_args[0]
    except:
        raise HTTP(400)

    s3base.s3_keep_messages()
    response.headers["Content-Type"] = "application/json"

    if len(req_args) > 1:
        output_level = int(req_args[1])
    else:
        output_level = None

    language = session.s3.language
    if language in ("en", "en-gb"):
        translate = False
    else:
        translate = settings.get_L10n_translate_gis_location()

    table = s3db.gis_location
    query = (table.deleted == False) & \
            (table.end_date == None) & \
            (table.level != None)
    if output_level:
        filter_level = output_level - 1
        query &= (table.level != "L%s" % filter_level) & \
                 ((table.path.like(location_id + "/%")) | \
                  (table.path.like("%/" + location_id + "/%")))
    else:
        query &= (table.parent == location_id)
    
    # Importing locally as in original file
    from core import LocationSelector
    fields, left = LocationSelector._get_location_fields(table, translate, language)

    locations = db((table.id == location_id) | query).select(*fields, left=left)

    location_id = int(location_id)
    # Logic omitted for brevity as we just want the call graph...
    # But keeping the structure regarding calls
    
    return json.dumps({}, separators=(',', ':'))
