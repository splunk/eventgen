import os
import sys
from shutil import copyfile, rmtree


def test_modular_input(mocker, capsys):
    # mock the splunk related module when used in modular input
    sys.modules['bundle_paths'] = __import__('splunk.clilib.bundle_paths')
    sys.modules['cli_common'] = __import__('splunk.clilib.cli_common')
    sys.modules['entity'] = __import__('splunk.entity')

    # eventgen base directory
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # insert modular input directory to the sys path
    mod_input_path = os.path.join(base_dir, 'splunk_eventgen', 'splunk_app', 'bin')
    sys.path.insert(0, mod_input_path)

    # create needed sample file
    simulated_splunk_etc_dir = os.path.dirname(os.path.dirname(base_dir))
    sample_path = os.path.join(simulated_splunk_etc_dir, 'modinput_test_app', 'samples')
    # os.mkdir(os.path.join(simulated_splunk_etc_dir, 'modinput_test_app'), 0666)
    os.makedirs(sample_path, 0o777)
    copyfile(os.path.join(base_dir, 'tests', 'large', 'sample', 'film.json'), os.path.join(sample_path, 'film.json'))

    from modinput_eventgen import Eventgen
    # input xml stream used to start modular input
    input_stream_path = os.path.join(base_dir, 'tests', 'large', 'splunk', 'input.xml')

    mocker.patch('sys.argv', ['', '--infile', input_stream_path])
    worker = Eventgen()
    worker.execute()

    # capture the generated events from std out
    captured = capsys.readouterr()
    assert "<stream>" in captured.out
    # assert "<data>" in captured.out
    # assert "<event>" in captured.out

    # remove above created simulated app folder
    rmtree(os.path.join(simulated_splunk_etc_dir, 'modinput_test_app'))

