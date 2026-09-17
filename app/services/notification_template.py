import logging
from typing import Dict, List
from jinja2 import Template, TemplateError, TemplateSyntaxError, TemplateNotFound

logger = logging.getLogger(__name__)

class NotificationTemplate:
    
    def __init__(self, name: str, subject_template: str, body_template: str):
        self.name = name
        self.subject_template = Template(subject_template)
        self.body_template = Template(body_template)
    
    def render(self, context: Dict) -> Dict[str, str]:

        try:
            subject = self.subject_template.render(**context)
            body = self.body_template.render(**context)
            return {"subject": subject, "body": body}
        except (TemplateError, TemplateSyntaxError) as e:
            logger.error(f"Template rendering error in {self.name}: {str(e)}")
            raise

class TemplateService:

    TEMPLATES = {
        "user_registered": NotificationTemplate(
            name="user_registered",
            subject_template="Welcome to Freelancer Marketplace, {{ user_name }}!",
            body_template="""
<html>
<body style="font-family: Arial, sans-serif; color: #333;">
    <h2>Welcome to Freelancer Marketplace!</h2>
    <p>Hi {{ user_name }},</p>
    <p>Thank you for signing up. Your account has been created successfully.</p>
    <p>
        <strong>Account Details:</strong><br>
        Email: {{ user_email }}<br>
        Role: {{ user_role }}
    </p>
    <p>You can now start exploring opportunities on our platform.</p>
    <p>
        <a href="{{ platform_url }}/dashboard" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
            Go to Dashboard
        </a>
    </p>
    <p>Best regards,<br>Freelancer Marketplace Team</p>
</body>
</html>
            """
        ),
        
        "proposal_received": NotificationTemplate(
            name="proposal_received",
            subject_template="New Proposal for Your Job: {{ job_title }}",
            body_template="""
<html>
<body style="font-family: Arial, sans-serif; color: #333;">
    <h2>New Proposal Received!</h2>
    <p>Hi {{ client_name }},</p>
    <p>You have received a new proposal for your job:</p>
    <p>
        <strong>{{ job_title }}</strong><br>
        Proposed Rate: ${{ proposed_rate }}/hour<br>
        Freelancer: {{ freelancer_name }}
    </p>
    <p>{{ freelancer_name }} has submitted the following proposal:</p>
    <blockquote style="border-left: 4px solid #ddd; padding-left: 16px; margin: 10px 0;">
        {{ cover_letter }}
    </blockquote>
    <p>
        <a href="{{ platform_url }}/jobs/{{ job_id }}/proposals" style="background-color: #28a745; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
            Review Proposal
        </a>
    </p>
    <p>Best regards,<br>Freelancer Marketplace Team</p>
</body>
</html>
            """
        ),
        
        "proposal_accepted": NotificationTemplate(
            name="proposal_accepted",
            subject_template="Your Proposal Was Accepted! 🎉",
            body_template="""
<html>
<body style="font-family: Arial, sans-serif; color: #333;">
    <h2>Congratulations! Your Proposal Was Accepted</h2>
    <p>Hi {{ freelancer_name }},</p>
    <p>Great news! Your proposal for the following job has been accepted:</p>
    <p>
        <strong>{{ job_title }}</strong><br>
        Client: {{ client_name }}<br>
        Proposed Rate: ${{ proposed_rate }}/hour
    </p>
    <p>The client is ready to move forward. A contract will be created soon.</p>
    <p>
        <a href="{{ platform_url }}/proposals/{{ proposal_id }}" style="background-color: #28a745; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
            View Details
        </a>
    </p>
    <p>Best regards,<br>Freelancer Marketplace Team</p>
</body>
</html>
            """
        ),
        
        "proposal_rejected": NotificationTemplate(
            name="proposal_rejected",
            subject_template="Update on Your Proposal for {{ job_title }}",
            body_template="""
<html>
<body style="font-family: Arial, sans-serif; color: #333;">
    <h2>Proposal Status Update</h2>
    <p>Hi {{ freelancer_name }},</p>
    <p>Thank you for submitting your proposal for:</p>
    <p><strong>{{ job_title }}</strong></p>
    <p>Unfortunately, {{ client_name }} has decided to move forward with another freelancer.</p>
    <p>Don't be discouraged! Keep applying to jobs that match your skills. You're doing great!</p>
    <p>
        <a href="{{ platform_url }}/jobs" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
            Browse More Jobs
        </a>
    </p>
    <p>Best regards,<br>Freelancer Marketplace Team</p>
</body>
</html>
            """
        ),
        
        "contract_created": NotificationTemplate(
            name="contract_created",
            subject_template="Contract Created for {{ job_title }}",
            body_template="""
<html>
<body style="font-family: Arial, sans-serif; color: #333;">
    <h2>Contract Created</h2>
    <p>Hi {{ user_name }},</p>
    <p>A contract has been created for your job:</p>
    <p>
        <strong>{{ job_title }}</strong><br>
        Freelancer: {{ freelancer_name }}<br>
        Amount: ${{ total_amount }}<br>
        Status: {{ status }}
    </p>
    <p>You can now start working together on the project.</p>
    <p>
        <a href="{{ platform_url }}/contracts/{{ contract_id }}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
            View Contract
        </a>
    </p>
    <p>Best regards,<br>Freelancer Marketplace Team</p>
</body>
</html>
            """
        ),
        
        "milestone_submitted": NotificationTemplate(
            name="milestone_submitted",
            subject_template="Milestone Submitted for Review: {{ milestone_title }}",
            body_template="""
<html>
<body style="font-family: Arial, sans-serif; color: #333;">
    <h2>Milestone Submitted for Review</h2>
    <p>Hi {{ client_name }},</p>
    <p>{{ freelancer_name }} has submitted the following milestone for your review:</p>
    <p>
        <strong>{{ milestone_title }}</strong><br>
        Amount: ${{ milestone_amount }}<br>
        Job: {{ job_title }}
    </p>
    <p>Please review the work and either approve or request revisions.</p>
    <p>
        <a href="{{ platform_url }}/milestones/{{ milestone_id }}" style="background-color: #28a745; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
            Review Milestone
        </a>
    </p>
    <p>Best regards,<br>Freelancer Marketplace Team</p>
</body>
</html>
            """
        ),
        
        "milestone_approved": NotificationTemplate(
            name="milestone_approved",
            subject_template="Your Milestone Was Approved! ✅",
            body_template="""
<html>
<body style="font-family: Arial, sans-serif; color: #333;">
    <h2>Milestone Approved!</h2>
    <p>Hi {{ freelancer_name }},</p>
    <p>Excellent news! Your milestone has been approved:</p>
    <p>
        <strong>{{ milestone_title }}</strong><br>
        Amount: ${{ milestone_amount }}<br>
        Job: {{ job_title }}
    </p>
    <p>Payment will be released shortly. Great work!</p>
    <p>
        <a href="{{ platform_url }}/contracts/{{ contract_id }}" style="background-color: #28a745; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
            View Contract
        </a>
    </p>
    <p>Best regards,<br>Freelancer Marketplace Team</p>
</body>
</html>
            """
        ),
        
        "milestone_rejected": NotificationTemplate(
            name="milestone_rejected",
            subject_template="Milestone Needs Revision: {{ milestone_title }}",
            body_template="""
<html>
<body style="font-family: Arial, sans-serif; color: #333;">
    <h2>Milestone Revision Requested</h2>
    <p>Hi {{ freelancer_name }},</p>
    <p>{{ client_name }} has reviewed your milestone and requested revisions:</p>
    <p>
        <strong>{{ milestone_title }}</strong><br>
        Reason: {{ rejection_reason }}
    </p>
    <p>Please make the requested changes and resubmit for review.</p>
    <p>
        <a href="{{ platform_url }}/milestones/{{ milestone_id }}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
            View Feedback
        </a>
    </p>
    <p>Best regards,<br>Freelancer Marketplace Team</p>
</body>
</html>
            """
        ),
        
        "contract_completed": NotificationTemplate(
            name="contract_completed",
            subject_template="Contract Completed! 🎊",
            body_template="""
<html>
<body style="font-family: Arial, sans-serif; color: #333;">
    <h2>Contract Completed</h2>
    <p>Hi {{ user_name }},</p>
    <p>The following contract has been completed:</p>
    <p>
        <strong>{{ job_title }}</strong><br>
        {% if is_freelancer %}Earned: ${{ total_amount }}{% else %}Paid: ${{ total_amount }}{% endif %}<br>
        Duration: {{ start_date }} to {{ end_date }}
    </p>
    <p>
        {% if is_freelancer %}
            Thank you for your excellent work! Consider leaving a review for your client.
        {% else %}
            Thank you for working with us. We hope to work with you again soon!
        {% endif %}
    </p>
    <p>
        <a href="{{ platform_url }}/contracts/{{ contract_id }}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
            View Contract Summary
        </a>
    </p>
    <p>Best regards,<br>Freelancer Marketplace Team</p>
</body>
</html>
            """
        ),
        
        "review_submitted": NotificationTemplate(
            name="review_submitted",
            subject_template="You've Received a Review from {{ reviewer_name }}",
            body_template="""
<html>
<body style="font-family: Arial, sans-serif; color: #333;">
    <h2>New Review Received</h2>
    <p>Hi {{ freelancer_name }},</p>
    <p>{{ reviewer_name }} has left you a review:</p>
    <p>
        <strong>Rating:</strong> {{ rating }} / 5 stars<br>
        <strong>Job:</strong> {{ job_title }}
    </p>
    <blockquote style="border-left: 4px solid #ddd; padding-left: 16px; margin: 10px 0;">
        {{ review_text }}
    </blockquote>
    <p>This review will help boost your profile and attract more clients!</p>
    <p>
        <a href="{{ platform_url }}/profile/{{ freelancer_id }}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
            View Your Profile
        </a>
    </p>
    <p>Best regards,<br>Freelancer Marketplace Team</p>
</body>
</html>
            """
        ),
    }
    
    @staticmethod
    def get_template(template_name: str) -> NotificationTemplate:

        if template_name not in TemplateService.TEMPLATES:
            available = list(TemplateService.TEMPLATES.keys())
            logger.error(f"Template '{template_name}' not found. Available: {available}")
            raise TemplateNotFound(f"Template '{template_name}' not found")
        
        return TemplateService.TEMPLATES[template_name]
    
    @staticmethod
    def list_templates() -> List[str]:
        return list(TemplateService.TEMPLATES.keys())