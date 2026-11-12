from pagecheck.audits.images.visual_rules import build_image_quality_findings


def img(*, width=200, height=100, nw=200, nh=100, fit="fill", loaded=True):
    return {"index": 0, "kind": "image", "complete": loaded,
            "natural_width": nw, "natural_height": nh, "object_fit": fit,
            "box": {"x": 12, "y": 50, "width": width, "height": height}}


def check(image):
    return build_image_quality_findings({"measured_elements": [image]})


def test_normal_image_is_clear():
    assert check(img()) == []


def test_upscaled_image_gets_review_warning():
    checks = check(img(width=200, height=100, nw=20, nh=10))
    assert [item["id"] for item in checks] == ["image-upscaled-0"]
    assert checks[0]["status"] == "warning"


def test_aspect_ratio_distortion_is_flagged():
    checks = check(img(width=300, height=100, nw=100, nh=100))
    assert any(item["id"] == "image-aspect-0" for item in checks)


def test_object_fit_cover_is_not_distortion():
    checks = check(img(width=300, height=100, nw=400, nh=400, fit="cover"))
    assert not any(item["id"].startswith("image-aspect") for item in checks)


def test_unloaded_image_is_not_claimed_distorted():
    assert check(img(width=200, height=100, nw=0, nh=0, loaded=False)) == []
