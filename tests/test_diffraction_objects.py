import re
from pathlib import Path

import numpy as np
import pytest
from deepdiff import DeepDiff
from freezegun import freeze_time

from diffpy.utils.diffraction_objects import XQUANTITIES, DiffractionObject


def compare_dicts(dict1, dict2):
    assert dict1.keys() == dict2.keys(), "Keys mismatch"
    for key in dict1:
        val1, val2 = dict1[key], dict2[key]
        if isinstance(val1, np.ndarray) and isinstance(val2, np.ndarray):
            assert np.allclose(val1, val2), f"Arrays for key '{key}' differ"
        elif isinstance(val1, np.float64) and isinstance(val2, np.float64):
            assert np.isclose(val1, val2), f"Float64 values for key '{key}' differ"
        else:
            assert val1 == val2, f"Values for key '{key}' differ: {val1} != {val2}"


def dicts_equal(dict1, dict2):
    equal = True
    print("")
    print(dict1)
    print(dict2)
    if not dict1.keys() == dict2.keys():
        equal = False
    for key in dict1:
        val1, val2 = dict1[key], dict2[key]
        if isinstance(val1, np.ndarray) and isinstance(val2, np.ndarray):
            if not np.allclose(val1, val2):
                equal = False
        elif isinstance(val1, list) and isinstance(val2, list):
            if not val1.all() == val2.all():
                equal = False
        elif isinstance(val1, np.float64) and isinstance(val2, np.float64):
            if not np.isclose(val1, val2):
                equal = False
        else:
            if not val1 == val2:
                equal = False
    return equal


params = [
    (  # Default
        {},
        {},
        True,
    ),
    (  # Compare same attributes
        {
            "name": "same",
            "scat_quantity": "x-ray",
            "wavelength": 0.71,
            "xtype": "q",
            "xarray": np.array([1.0, 2.0]),
            "yarray": np.array([100.0, 200.0]),
            "metadata": {"thing1": 1},
        },
        {
            "name": "same",
            "scat_quantity": "x-ray",
            "wavelength": 0.71,
            "xtype": "q",
            "xarray": np.array([1.0, 2.0]),
            "yarray": np.array([100.0, 200.0]),
            "metadata": {"thing1": 1},
        },
        True,
    ),
    (  # Different names
        {
            "name": "something",
            "scat_quantity": "",
            "wavelength": None,
            "xtype": "",
            "xarray": np.empty(0),
            "yarray": np.empty(0),
            "metadata": {"thing1": 1, "thing2": "thing2"},
        },
        {
            "name": "something else",
            "scat_quantity": "",
            "wavelength": None,
            "xtype": "",
            "xarray": np.empty(0),
            "yarray": np.empty(0),
            "metadata": {"thing1": 1, "thing2": "thing2"},
        },
        False,
    ),
    (  # Different wavelengths
        {
            "scat_quantity": "",
            "wavelength": 0.71,
            "xtype": "",
            "xarray": np.empty(0),
            "yarray": np.empty(0),
            "metadata": {"thing1": 1, "thing2": "thing2"},
        },
        {
            "scat_quantity": "",
            "wavelength": None,
            "xtype": "",
            "xarray": np.empty(0),
            "yarray": np.empty(0),
            "metadata": {"thing1": 1, "thing2": "thing2"},
        },
        False,
    ),
    (  # Different wavelengths
        {
            "scat_quantity": "",
            "wavelength": 0.71,
            "xtype": "",
            "xarray": np.empty(0),
            "yarray": np.empty(0),
            "metadata": {"thing1": 1, "thing2": "thing2"},
        },
        {
            "scat_quantity": "",
            "wavelength": 0.711,
            "xtype": "",
            "xarray": np.empty(0),
            "yarray": np.empty(0),
            "metadata": {"thing1": 1, "thing2": "thing2"},
        },
        False,
    ),
    (  # Different scat_quantity
        {
            "scat_quantity": "x-ray",
            "wavelength": None,
            "xtype": "",
            "xarray": np.empty(0),
            "yarray": np.empty(0),
            "metadata": {"thing1": 1, "thing2": "thing2"},
        },
        {
            "scat_quantity": "neutron",
            "wavelength": None,
            "xtype": "",
            "xarray": np.empty(0),
            "yarray": np.empty(0),
            "metadata": {"thing1": 1, "thing2": "thing2"},
        },
        False,
    ),
    (  # Different on_q
        {
            "scat_quantity": "",
            "wavelength": None,
            "xtype": "q",
            "xarray": np.array([1.0, 2.0]),
            "yarray": np.array([100.0, 200.0]),
            "metadata": {},
        },
        {
            "scat_quantity": "",
            "wavelength": None,
            "xtype": "q",
            "xarray": np.array([3.0, 4.0]),
            "yarray": np.array([100.0, 200.0]),
            "metadata": {"thing1": 1, "thing2": "thing2"},
        },
        False,
    ),
    (  # Different metadata
        {
            "scat_quantity": "",
            "wavelength": None,
            "xtype": "",
            "xarray": np.empty(0),
            "yarray": np.empty(0),
            "metadata": {"thing1": 0, "thing2": "thing2"},
        },
        {
            "scat_quantity": "",
            "wavelength": None,
            "xtype": "",
            "xarray": np.empty(0),
            "yarray": np.empty(0),
            "metadata": {"thing1": 1, "thing2": "thing2"},
        },
        False,
    ),
]


@pytest.mark.parametrize("inputs1, inputs2, expected", params)
def test_diffraction_objects_equality(inputs1, inputs2, expected):
    diffraction_object1 = DiffractionObject(**inputs1)
    diffraction_object2 = DiffractionObject(**inputs2)
    # diffraction_object1_attributes = [key for key in diffraction_object1.__dict__ if not key.startswith("_")]
    # for i, attribute in enumerate(diffraction_object1_attributes):
    #     setattr(diffraction_object1, attribute, inputs1[i])
    #     setattr(diffraction_object2, attribute, inputs2[i])
    print(dicts_equal(diffraction_object1.__dict__, diffraction_object2.__dict__), expected)
    assert dicts_equal(diffraction_object1.__dict__, diffraction_object2.__dict__) == expected


def test_on_xtype():
    test = DiffractionObject(wavelength=2 * np.pi, xarray=np.array([30, 60]), yarray=np.array([1, 2]), xtype="tth")
    assert np.allclose(test.on_xtype("tth"), [np.array([30, 60]), np.array([1, 2])])
    assert np.allclose(test.on_xtype("2theta"), [np.array([30, 60]), np.array([1, 2])])
    assert np.allclose(test.on_xtype("q"), [np.array([0.51764, 1]), np.array([1, 2])])
    assert np.allclose(test.on_xtype("d"), [np.array([12.13818, 6.28319]), np.array([1, 2])])


def test_on_xtype_bad():
    test = DiffractionObject()
    with pytest.raises(
        ValueError,
        match=re.escape(
            f"I don't know how to handle the xtype, 'invalid'. Please rerun specifying an "
            f"xtype from {*XQUANTITIES, }"
        ),
    ):
        test.on_xtype("invalid")


params_index = [
    # UC1: exact match
    ([4 * np.pi, np.array([30.005, 60]), np.array([1, 2]), "tth", "tth", 30.005], [0]),
    # UC2: target value lies in the array, returns the (first) closest index
    ([4 * np.pi, np.array([30, 60]), np.array([1, 2]), "tth", "tth", 45], [0]),
    ([4 * np.pi, np.array([30, 60]), np.array([1, 2]), "tth", "q", 0.25], [0]),
    # UC3: target value out of the range, returns the closest index
    ([4 * np.pi, np.array([0.25, 0.5, 0.71]), np.array([1, 2, 3]), "q", "q", 0.1], [0]),
    ([4 * np.pi, np.array([30, 60]), np.array([1, 2]), "tth", "tth", 63], [1]),
]


@pytest.mark.parametrize("inputs, expected", params_index)
def test_get_array_index(inputs, expected):
    test = DiffractionObject(wavelength=inputs[0], xarray=inputs[1], yarray=inputs[2], xtype=inputs[3])
    actual = test.get_array_index(value=inputs[5], xtype=inputs[4])
    assert actual == expected[0]


def test_get_array_index_bad():
    test = DiffractionObject(wavelength=2 * np.pi, xarray=np.array([]), yarray=np.array([]), xtype="tth")
    with pytest.raises(ValueError, match=re.escape("The 'tth' array is empty. Please ensure it is initialized.")):
        test.get_array_index(value=30)


def test_dump(tmp_path, mocker):
    x, y = np.linspace(0, 5, 6), np.linspace(0, 5, 6)
    directory = Path(tmp_path)
    file = directory / "testfile"
    test = DiffractionObject(
        wavelength=1.54,
        name="test",
        scat_quantity="x-ray",
        xarray=np.array(x),
        yarray=np.array(y),
        xtype="q",
        metadata={"thing1": 1, "thing2": "thing2", "package_info": {"package2": "3.4.5"}},
    )
    mocker.patch("importlib.metadata.version", return_value="3.3.0")
    with freeze_time("2012-01-14"):
        test.dump(file, "q")
    with open(file, "r") as f:
        actual = f.read()
    expected = (
        "[DiffractionObject]\nname = test\nwavelength = 1.54\nscat_quantity = x-ray\nthing1 = 1\n"
        "thing2 = thing2\npackage_info = {'package2': '3.4.5', 'diffpy.utils': '3.3.0'}\n"
        "creation_time = 2012-01-14 00:00:00\n\n"
        "#### start data\n0.000000000000000000e+00 0.000000000000000000e+00\n"
        "1.000000000000000000e+00 1.000000000000000000e+00\n"
        "2.000000000000000000e+00 2.000000000000000000e+00\n"
        "3.000000000000000000e+00 3.000000000000000000e+00\n"
        "4.000000000000000000e+00 4.000000000000000000e+00\n"
        "5.000000000000000000e+00 5.000000000000000000e+00\n"
    )

    assert actual == expected


tc_params = [
    (
        {},
        {
            "_all_arrays": np.empty(shape=(0, 4)),  # instantiate empty
            "metadata": {},
            "input_xtype": "",
            "name": "",
            "scat_quantity": None,
            "qmin": np.float64(np.inf),
            "qmax": np.float64(0.0),
            "tthmin": np.float64(np.inf),
            "tthmax": np.float64(0.0),
            "dmin": np.float64(np.inf),
            "dmax": np.float64(0.0),
            "wavelength": None,
        },
    ),
    (  # instantiate just non-array attributes
        {"name": "test", "scat_quantity": "x-ray", "metadata": {"thing": "1", "another": "2"}},
        {
            "_all_arrays": np.empty(shape=(0, 4)),
            "metadata": {"thing": "1", "another": "2"},
            "input_xtype": "",
            "name": "test",
            "scat_quantity": "x-ray",
            "qmin": np.float64(np.inf),
            "qmax": np.float64(0.0),
            "tthmin": np.float64(np.inf),
            "tthmax": np.float64(0.0),
            "dmin": np.float64(np.inf),
            "dmax": np.float64(0.0),
            "wavelength": None,
        },
    ),
    (  # instantiate just array attributes
        {
            "xarray": np.array([0.0, 90.0, 180.0]),
            "yarray": np.array([1.0, 2.0, 3.0]),
            "xtype": "tth",
            "wavelength": 4.0 * np.pi,
        },
        {
            "_all_arrays": np.array(
                [
                    [1.0, 0.0, 0.0, np.float64(np.inf)],
                    [2.0, 1.0 / np.sqrt(2), 90.0, np.sqrt(2) * 2 * np.pi],
                    [3.0, 1.0, 180.0, 1.0 * 2 * np.pi],
                ]
            ),
            "metadata": {},
            "input_xtype": "tth",
            "name": "",
            "scat_quantity": None,
            "qmin": np.float64(0.0),
            "qmax": np.float64(1.0),
            "tthmin": np.float64(0.0),
            "tthmax": np.float64(180.0),
            "dmin": np.float64(2 * np.pi),
            "dmax": np.float64(np.inf),
            "wavelength": 4.0 * np.pi,
        },
    ),
    (  # instantiate just array attributes
        {
            "xarray": np.array([np.inf, 2 * np.sqrt(2) * np.pi, 2 * np.pi]),
            "yarray": np.array([1.0, 2.0, 3.0]),
            "xtype": "d",
            "wavelength": 4.0 * np.pi,
            "scat_quantity": "x-ray",
        },
        {
            "_all_arrays": np.array(
                [
                    [1.0, 0.0, 0.0, np.float64(np.inf)],
                    [2.0, 1.0 / np.sqrt(2), 90.0, np.sqrt(2) * 2 * np.pi],
                    [3.0, 1.0, 180.0, 1.0 * 2 * np.pi],
                ]
            ),
            "metadata": {},
            "input_xtype": "d",
            "name": "",
            "scat_quantity": "x-ray",
            "qmin": np.float64(0.0),
            "qmax": np.float64(1.0),
            "tthmin": np.float64(0.0),
            "tthmax": np.float64(180.0),
            "dmin": np.float64(2 * np.pi),
            "dmax": np.float64(np.inf),
            "wavelength": 4.0 * np.pi,
        },
    ),
]


@pytest.mark.parametrize("inputs, expected", tc_params)
def test_constructor(inputs, expected):
    actual_do = DiffractionObject(**inputs)
    diff = DeepDiff(actual_do.__dict__, expected, ignore_order=True, significant_digits=13)
    assert diff == {}


def test_all_array_getter():
    actual_do = DiffractionObject(
        xarray=np.array([0.0, 90.0, 180.0]),
        yarray=np.array([1.0, 2.0, 3.0]),
        xtype="tth",
        wavelength=4.0 * np.pi,
    )
    expected_all_arrays = np.array(
        [
            [1.0, 0.0, 0.0, np.float64(np.inf)],
            [2.0, 1.0 / np.sqrt(2), 90.0, np.sqrt(2) * 2 * np.pi],
            [3.0, 1.0, 180.0, 1.0 * 2 * np.pi],
        ]
    )
    assert np.allclose(actual_do.all_arrays, expected_all_arrays)


def test_all_array_setter():
    actual_do = DiffractionObject()

    # Attempt to directly modify the property
    with pytest.raises(
        AttributeError,
        match="Direct modification of attribute 'all_arrays' is not allowed."
        "Please use 'insert_scattering_quantity' to modify `all_arrays`.",
    ):
        actual_do.all_arrays = np.empty((4, 4))


def test_copy_object():
    do = DiffractionObject(
        name="test",
        wavelength=4.0 * np.pi,
        xarray=np.array([0.0, 90.0, 180.0]),
        yarray=np.array([1.0, 2.0, 3.0]),
        xtype="tth",
    )
    do_copy = do.copy()
    assert do == do_copy
    assert id(do) != id(do_copy)
