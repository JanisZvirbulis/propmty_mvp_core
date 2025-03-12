from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage

class MediaStorage(S3Boto3Storage):
    location = 'media'  # Bāzes direktorija S3 bucket
    file_overwrite = False
    default_acl = None
    custom_domain = f'{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'

# Varat saglabāt esošās augšupielādes ceļu funkcijas model.py failos
# un tad izmantot šīs storage klases bez location norādīšanas:

class CompanyStorage(MediaStorage):
    """Storage klase uzņēmuma datiem (logo, u.c.)"""
    # Location netiek norādīts, lai varētu pilnībā izmantot
    # get_company_logo_upload_path funkciju

class IssueImageStorage(MediaStorage):
    """Storage klase problēmu attēliem"""
    # Location netiek norādīts, lai varētu pilnībā izmantot
    # get_report_Issue_image_upload_path funkciju

class ProfileImageStorage(MediaStorage):
    """Storage klase lietotāju profila attēliem"""
    location = 'media/profile_images'  # Šeit varam norādīt direktoriju