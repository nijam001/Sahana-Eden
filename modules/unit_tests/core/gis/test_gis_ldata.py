# Eden Unit Tests
#
# To run this script use:
# python web2py.py -S eden -M -R applications/eden/modules/unit_tests/core/gis/test_gis_ldata.py
#

import unittest
import os
import json
import datetime
from gluon import current, HTTP
from gluon.storage import Storage

import core as s3base
from unit_tests import run_suite

# =============================================================================
class GisLdataTests(unittest.TestCase):
    """ Tests for gis.ldata controller function """

    # -------------------------------------------------------------------------
    def setUp(self):

        self.original_request = current.request
        self.original_response = current.response
        self.original_session = current.session
        
        current.auth.override = True
        try:
            current.db.executesql("PRAGMA foreign_keys = OFF;")
        except:
            pass

        # Mock Request
        request = Storage()
        request.controller = "gis"
        request.function = "ldata"
        request.extension = "json"
        request.folder = self.original_request.folder
        request.application = self.original_request.application
        request.args = []
        request.vars = Storage()
        request.get_vars = Storage()
        request.post_vars = Storage()
        request.env = Storage()
        request.utcnow = datetime.datetime.utcnow()
        current.request = request

        # Mock Response
        response = Storage()
        response.headers = {}
        response.s3 = Storage()
        response.s3.crud_strings = Storage()
        current.response = response

        # Mock Session
        session = Storage()
        session.s3 = Storage()
        session.s3.language = "en"
        current.session = session

        # Prepare environment for controller execution
        self.env = {
            "request": current.request,
            "response": current.response,
            "session": current.session,
            "T": current.T,
            "db": current.db,
            "s3db": current.s3db,
            "auth": current.auth,
            "settings": current.deployment_settings,
            "s3": current.response.s3,
            "appname": current.request.application,
            "get_vars": current.request.get_vars,
            "current": current,
            "s3base": s3base,
            "json": json,
            "HTTP": HTTP,
        }

        # Load the controller
        path = os.path.join(request.folder, "controllers", "gis.py")
        with open(path, "r") as f:
            code = f.read()

        # Execute the controller code to get the ldata function
        # We wrap it in a try-except because executing the whole file might trigger
        # code that expects more setup (though we tried to provide enough)
        try:
            exec(code, self.env)
        except Exception as e:
            # If it fails, we might still have ldata defined if it failed after definition
            if "ldata" not in self.env:
                raise e

        self.ldata = self.env["ldata"]

    # -------------------------------------------------------------------------
    def tearDown(self):

        current.auth.override = False
        current.request = self.original_request
        current.response = self.original_response
        current.session = self.original_session

    # -------------------------------------------------------------------------
    def test_ldata_no_args(self):
        """ Test ldata with no arguments (should raise HTTP 400) """

        current.request.args = []
        try:
            self.ldata()
            self.fail("HTTP 400 not raised")
        except HTTP as e:
            self.assertEqual(e.status, 400)

    # -------------------------------------------------------------------------
    def test_ldata_valid_location(self):
        """ Test ldata with a valid location ID """

        # Insert a test location
        table = current.s3db.gis_location
        location_id = table.insert(name="Test Location Ldata", level="L0")
        current.db(table.id == location_id).update(path=str(location_id))
        current.db.commit()

        try:
            current.request.args = [str(location_id)]
            output = self.ldata()
            
            # Parse JSON output
            data = json.loads(output)
            
            # Check if the location is in the output
            # ldata returns a dict where keys are location IDs
            self.assertIn(str(location_id), data)
            self.assertEqual(data[str(location_id)]["n"], "Test Location Ldata")

        finally:
            # Clean up
            current.db(table.id == location_id).delete()
            current.db.commit()

    # -------------------------------------------------------------------------
    def test_ldata_with_level(self):
        """ Test ldata with location ID and level """

        # Insert a hierarchy
        table = current.s3db.gis_location
        l0_id = table.insert(name="Test L0", level="L0")
        l1_id = table.insert(name="Test L1", level="L1", parent=l0_id)
        
        # Manually update path since onaccept is not called and async tasks are not running
        current.db(table.id == l0_id).update(path=str(l0_id))
        current.db(table.id == l1_id).update(path="%s/%s" % (l0_id, l1_id))
        
        current.db.commit()

        try:
            # Request children of L0 at level 1
            current.request.args = [str(l0_id), "1"]
            output = self.ldata()
            
            data = json.loads(output)
            
            # Should contain L1
            self.assertIn(str(l1_id), data)
            self.assertEqual(data[str(l1_id)]["n"], "Test L1")
            
        finally:
            current.db(table.id.belongs((l0_id, l1_id))).delete()
            current.db.commit()

# =============================================================================
if __name__ == "__main__":

    run_suite(
        GisLdataTests,
    )

# END ========================================================================
