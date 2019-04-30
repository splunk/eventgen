import os


def make_splunkhome_path(*args):
    splunk_test_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    tests_large_dir = os.path.dirname(splunk_test_dir)
    return os.path.join(tests_large_dir, 'results', 'test_modinput.log')
