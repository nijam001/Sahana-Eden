import unittest

class TestAssignment2Testing(unittest.TestCase):

    def test_sanity(self):
        # Basic sanity check: proves the test framework works
        self.assertEqual(1 + 1, 2)

    def test_email_format(self):
        # Simple validation-like test
        email = "user@test.com"
        self.assertIn("@", email)
        self.assertIn(".", email)

    def test_string_length(self):
        # Example of another simple logic test
        password = "secret123"
        self.assertTrue(len(password) >= 6)

if __name__ == "__main__":
    unittest.main()
