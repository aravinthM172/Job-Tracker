from live_jobs.companies import is_target_company


def test_exact_name_matches():
    assert is_target_company("Google")
    assert is_target_company("Razorpay")
    assert is_target_company("Bank of America")


def test_case_and_punctuation_insensitive():
    assert is_target_company("  google ")
    assert is_target_company("NVIDIA!!")


def test_descriptive_suffix_on_either_side_matches():
    # ATS names a company more/less specifically than companies.py does
    assert is_target_company("KPMG Global Services")  # list has "KPMG"
    assert is_target_company("Samsung")  # list has "Samsung R&D Institute India"


def test_off_list_companies_are_rejected():
    for name in ("Autodesk", "Netradyne", "Roku", "Temporal", "Reddit", "Figma"):
        assert not is_target_company(name)


def test_blank_is_rejected():
    assert not is_target_company("")
    assert not is_target_company(None)
