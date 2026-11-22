import os, sys
sys.path.insert(0, '/home/hatch/workspace/clipping-website/openshorts')
import s3_uploader
from unittest import mock

# (a) B2 endpoint set -> boto3.client gets endpoint_url
os.environ.update({"AWS_ACCESS_KEY_ID": "test-key-id", "AWS_SECRET_ACCESS_KEY": "test-secret",
                   "AWS_REGION": "us-west-004", "S3_ENDPOINT_URL": "https://s3.us-west-004.backblazeb2.com"})
with mock.patch("s3_uploader.boto3.client") as m:
    m.return_value = mock.MagicMock()
    s3_uploader.get_s3_client()
    kw = m.call_args
    print("B2 client call:", kw)
    assert kw.kwargs.get("endpoint_url") == "https://s3.us-west-004.backblazeb2.com", "endpoint_url missing!"
    assert kw.kwargs.get("region_name") == "us-west-004"
    print("B2 endpoint_url: PASS")
    print("B2 public URL:", s3_uploader._public_url("my-bucket", "clips/a.mp4", "us-west-004"))
    assert s3_uploader._public_url("my-bucket", "clips/a.mp4", "us-west-004") == \
        "https://s3.us-west-004.backblazeb2.com/my-bucket/clips/a.mp4"
    print("B2 public URL: PASS")

# (b) No endpoint -> upstream AWS behaviour unchanged
del os.environ["S3_ENDPOINT_URL"]
with mock.patch("s3_uploader.boto3.client") as m:
    m.return_value = mock.MagicMock()
    s3_uploader.get_s3_client()
    assert "endpoint_url" not in m.call_args.kwargs, "endpoint_url leaked into AWS call!"
    print("AWS default (no endpoint_url): PASS")
    assert s3_uploader._public_url("my-bucket", "clips/a.mp4", "eu-west-3") == \
        "https://my-bucket.s3.eu-west-3.amazonaws.com/clips/a.mp4"
    print("AWS public URL: PASS")

# (c) upload_file_to_s3 passes endpoint through, returns False without real creds path
os.environ["S3_ENDPOINT_URL"] = "https://s3.us-west-004.backblazeb2.com"
with mock.patch("s3_uploader.boto3.client") as m:
    m.return_value.upload_file.return_value = None
    assert s3_uploader.upload_file_to_s3("/tmp/x.mp4", "b", "k") is True
    assert m.call_args.kwargs.get("endpoint_url") == "https://s3.us-west-004.backblazeb2.com"
    print("upload_file_to_s3 with B2 endpoint: PASS")
print("ALL B2 PATCH TESTS PASSED")
