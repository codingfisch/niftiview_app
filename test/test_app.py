import unittest

from niftiview_app.main import NiftiView
from niftiview_app.utils import Config


class TestCBar(unittest.TestCase):
    def test_init(self):
        config = Config()
        app = NiftiView(config)
        self.assertIsInstance(app, NiftiView)


if __name__ == "__main__":
    unittest.main()
