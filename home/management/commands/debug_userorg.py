from django.core.management.base import BaseCommand
from home.models import Organization, UserProfile, UserOrganization
import sys

class Command(BaseCommand):
    

    def handle(self, *args, **options):
        self.stdout.write('=== Organizations ===')
        orgs = Organization.objects.all()
        for org in orgs:
            self.stdout.write(f'ID: {org.id}, Name: {org.name}')
        
        self.stdout.write('\n=== User Profiles ===')
        profiles = UserProfile.objects.all()
        for profile in profiles:
            self.stdout.write(f'ID: {profile.id}, User: {profile.user.username}, Role: {profile.role}')
        
        self.stdout.write('\n=== UserOrganization Relationships ===')
        user_orgs = UserOrganization.objects.all()
        if user_orgs.exists():
            for user_org in user_orgs:
                self.stdout.write(f'ID: {user_org.id}, User: {user_org.user.user.username}, '
                                f'Org: {user_org.organization.name}, Level: {user_org.level}')
        else:
            self.stdout.write('No UserOrganization relationships found.')
            
        self.stdout.write('\n=== Test UserOrganization Creation ===')
        try:
            # Attempt to create a test UserOrg (if there's at least one profile and org)
            if profiles.exists() and orgs.exists():
                test_profile = profiles.first()
                test_org = orgs.first()
                test_user_org = UserOrganization.objects.create(
                    user=test_profile,
                    organization=test_org,
                    level=1
                )
                self.stdout.write(f'Successfully created test UserOrg: {test_user_org.id}')
                # Clean up
                test_user_org.delete()
                self.stdout.write('Test UserOrg deleted.')
            else:
                self.stdout.write('Cannot test - need at least one UserProfile and one Organization')
        except Exception as e:
            self.stdout.write(f'Error creating test UserOrg: {str(e)}')
            self.stdout.write(f'Error type: {type(e).__name__}')
            self.stdout.write(f'Python version: {sys.version}')
