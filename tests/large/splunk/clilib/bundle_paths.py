import os


def make_splunkhome_path(*args):
    tests_dir = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
    project_dir = os.path.dirname(tests_dir)
    return os.path.join(project_dir, "splunk_eventgen", "splunk_app", "lib")


def get_slaveapps_base_path():
    pass
