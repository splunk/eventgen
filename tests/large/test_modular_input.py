import os
import sys


def test_modular_input(mocker, capsys):
    # mock the splunk related module when used in modular input
    sys.modules["bundle_paths"] = __import__("splunk.clilib.bundle_paths")
    sys.modules["cli_common"] = __import__("splunk.clilib.cli_common")
    sys.modules["entity"] = __import__("splunk.entity")

    # eventgen base directory
    base_dir = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )

    from splunk_eventgen.splunk_app.bin.modinput_eventgen import Eventgen

    # input xml stream used to start modular input
    input_stream_path = os.path.join(base_dir, "tests", "large", "splunk", "input.xml")

    mocker.patch("sys.argv", ["", "--infile", input_stream_path])
    worker = Eventgen()
    worker.execute()

    # capture the generated events from std out
    captured = capsys.readouterr()
    assert "<stream>" in captured.out
    assert "<data>" in captured.out
    assert "<event>" in captured.out
