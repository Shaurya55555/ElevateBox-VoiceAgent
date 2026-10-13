import messages

PHONE = "+91-7985200306"


def test_postcall_uses_real_context_and_phone():
    facts = {"product_type": "handmade candles", "product_count": "40",
             "budget": "around 50k", "timeline": "next month"}
    text = messages.postcall_message(facts, PHONE)
    assert "handmade candles" in text
    assert "40" in text and "50k" in text and "next month" in text
    assert PHONE in text


def test_postcall_references_barrier_and_callback():
    text = messages.postcall_message(
        {"barrier": "checking with my partner", "callback_time": "tomorrow 10am"}, PHONE)
    assert "checking with my partner" in text
    assert "tomorrow 10am" in text


def test_postcall_with_no_facts_still_has_phone():
    text = messages.postcall_message({}, PHONE)
    assert PHONE in text
    assert "Sounds like" not in text


def test_midcall_lists_known_facts_only():
    text = messages.midcall_message({"budget": "1 lakh"}, PHONE)
    assert "Budget: 1 lakh" in text
    assert "Timeline" not in text


def test_template_params_have_fallbacks():
    params = messages.template_params_followup({}, PHONE)
    assert params[1] == PHONE
    assert params[0]
