"""Prepare GlitchTip for the app: an admin, an organization, a project and a fixed DSN.

Run by the glitchtip-setup service (`manage.py shell < bootstrap.py`) every time the
stack starts; it is idempotent. The DSN key is fixed so the Compose file can hand it
to the app without a manual step. Local use only: the key and password are not secrets.
"""

import os
import uuid

from allauth.account.models import EmailAddress
from apps.organizations_ext.models import Organization
from apps.projects.models import Project, ProjectKey
from apps.teams.models import Team
from apps.users.models import User

EMAIL = os.environ["GLITCHTIP_ADMIN_EMAIL"]
PASSWORD = os.environ["GLITCHTIP_ADMIN_PASSWORD"]
PUBLIC_KEY = uuid.UUID(os.environ["GLITCHTIP_PUBLIC_KEY"])

user = User.objects.filter(email=EMAIL).first()
if user is None:
    user = User.objects.create_superuser(email=EMAIL, password=PASSWORD)
EmailAddress.objects.get_or_create(
    user=user, email=EMAIL, defaults={"primary": True, "verified": True}
)

# GlitchTip derives (and deduplicates) slugs from names, so everything is found by name.
org = Organization.objects.filter(name="FinnancialSystem").order_by("pk").first()
if org is None:
    org = Organization.objects.create(name="FinnancialSystem")
if not org.users.filter(pk=user.pk).exists():
    org.add_user(user)

project = Project.objects.filter(organization=org, name="Backend").order_by("pk").first()
if project is None:
    project = Project.objects.create(organization=org, name="Backend", platform="python")
team, _ = Team.objects.get_or_create(slug="finnancial", organization=org)
team.members.add(org.organization_users.get(user=user))
team.projects.add(project)

# GlitchTip gives a new project a random key; the first time, it becomes the fixed one.
if not ProjectKey.objects.filter(project=project, public_key=PUBLIC_KEY).exists():
    key = ProjectKey.objects.filter(project=project).order_by("pk").first()
    if key is None:
        ProjectKey.objects.create(project=project, public_key=PUBLIC_KEY)
    else:
        ProjectKey.objects.filter(pk=key.pk).update(public_key=PUBLIC_KEY)

print(f"GlitchTip ready: project {project.id}, DSN key {PUBLIC_KEY.hex}")
