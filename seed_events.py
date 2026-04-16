"""Seed script: creates accounts, sources, links, and 200 events.

Run inside the web container:
    docker exec python-demo-web python seed_events.py
"""

import random
import time

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Account, QueuedEventRequest, Source, account_sources
from celery_app import celery_app

SALESFORCE_PAYLOADS = [
    "Lead conversion completed for contact Maria Chen at Brightwave Technologies. Deal value estimated at $45,000 annually. Sales rep John Torres updated the opportunity stage to Closed Won. The contract includes premium support and onboarding services for their engineering team of twelve members.",
    "Opportunity stage changed from Proposal to Negotiation for GlobalSync Inc. Account executive Sarah Patel scheduled a follow-up meeting for next Tuesday. The deal involves migrating their existing CRM data from a legacy system and provisioning fifty user licenses across three departments.",
    "New case opened by customer Apex Digital Solutions regarding data synchronization failures between their Salesforce instance and the external billing platform. Priority set to high. The sync has been failing intermittently for the past seventy-two hours affecting invoice generation workflows.",
    "Contact record updated for James Rodriguez at Meridian Healthcare. New email address and phone number added after company restructuring. The account ownership was transferred from the West Coast team to the Central region team effective immediately per the territory realignment.",
    "Campaign performance report generated for Q1 Spring Launch initiative. Total leads captured: 847. Conversion rate: twelve percent. Cost per acquisition: $23.50. The campaign targeted mid-market SaaS companies in the healthcare and financial services verticals across North America.",
    "Account merge completed for duplicate records of Pinnacle Enterprises. Primary account retained ID SF-209481. Secondary account SF-318276 was deprecated. All related opportunities, contacts, and case histories were migrated to the primary account without data loss.",
    "Task auto-assigned to sales rep Diana Morales for follow-up with Horizon Labs after their trial period expires in seven days. The prospect has been actively using the analytics dashboard and has added three additional team members during the evaluation period.",
    "Price book update applied to Enterprise Tier products. Annual subscription increased by eight percent effective next billing cycle. Existing contracts with locked pricing are excluded from this adjustment. Notification emails were sent to all affected account managers for review.",
    "Web-to-lead form submission received from visitor at trade show landing page. Name: Kevin Park, Company: Stratos Innovations, Role: VP of Engineering. Interest area: API integration capabilities and custom workflow automation for their product development pipeline.",
    "Approval process triggered for discount request on deal with Quantum Retail Group. Requested discount: fifteen percent on a three-year commitment. Sales director approval required for discounts exceeding ten percent. Deal size: $128,000 total contract value.",
    "Scheduled report delivery failed for weekly pipeline summary to distribution list sales-leadership@company.com. Error: SMTP timeout after thirty seconds. The report contains pipeline data for forty-two active opportunities across the enterprise sales segment.",
    "Custom object record created for partner referral from TechBridge Consulting. Referral contact: Lisa Nguyen. Referred prospect: DataVault Corp. Expected deal size: $67,000. Partner commission tier: Gold level at eight percent of first year revenue.",
    "Chatter post flagged for review in the All Company group. User Mike Sullivan shared competitive intelligence about rival product pricing changes. The post mentions specific pricing figures that may need verification before broader distribution to the sales team.",
    "Einstein lead scoring model updated with fresh training data from the last quarter. Top predictive factors: company size, industry vertical, website engagement frequency, and number of content downloads. Model accuracy improved from seventy-one to seventy-eight percent.",
    "Bulk data import completed for marketing event attendee list. Records processed: 312. New leads created: 189. Existing contacts updated: 98. Duplicates skipped: 25. Source campaign: Annual Industry Summit 2024 held in Chicago last week.",
    "Workflow rule fired for overdue renewal notification. Account: Silverline Media Group. Renewal date: fourteen days ago. Current contract value: $34,500. Account health score: amber. Last customer interaction was twenty-eight days ago via support ticket.",
    "Knowledge article published by support agent Rachel Kim titled Troubleshooting SSO Configuration Errors. Article covers common SAML assertion failures, certificate expiration handling, and identity provider metadata refresh procedures for enterprise single sign-on setups.",
    "Territory reassignment batch job completed. Total accounts moved: 156. Accounts moved to West region: 43. Accounts moved to East region: 67. Accounts moved to Central region: 46. All related open opportunities retained their original owner assignments.",
    "Integration sync log for Salesforce to ERP connection shows 4,218 records processed successfully. Three records failed validation due to missing required fields: purchase order number. Failed records queued for manual review by the operations team.",
    "Forecast submission received from sales director Tom Bradley for Q2. Committed amount: $1.2 million. Best case: $1.8 million. Pipeline total: $3.4 million. Commentary notes strong momentum in the healthcare vertical and two large enterprise deals expected to close.",
]

SLACK_PAYLOADS = [
    "Channel notification in #engineering-alerts: Deployment pipeline for service auth-gateway completed successfully. Build number 4821. All integration tests passed. Rollout to production cluster us-east-1 finished in twelve minutes with zero downtime. Monitoring dashboards show normal latency metrics.",
    "Direct message from bot: Your scheduled reminder to review pull request number 347 on the payments-service repository. The PR has been open for three days and has two approved reviews but requires one more from the platform team before merging.",
    "User Emily Chang updated the channel topic in #product-launches to: Beta release of Dashboard v3 scheduled for April 28th. All feature flags should be verified in staging by end of week. Design assets are finalized and uploaded to the shared Figma workspace.",
    "Thread reply in #customer-success from agent Mark Torres: Escalation for Brightwave account resolved. Root cause was a misconfigured webhook endpoint on their side. Customer confirmed the integration is working correctly after updating their callback URL to the new format.",
    "Workflow triggered in #sales-ops: New deal alert. Opportunity Quantum Retail Group moved to Closed Won. Deal value: $128,000 over three years. Account executive: Diana Morales. This is the largest deal closed in the mid-market segment this quarter.",
    "App notification from Jira integration in #sprint-board: Sprint 47 retrospective summary posted. Team velocity: 84 story points. Completed stories: 14 out of 17. Three stories carried over to next sprint due to dependency on the external API migration project.",
    "Pinned message in #company-announcements by CEO: We are excited to announce our Series B funding round of $42 million led by Summit Ventures. This investment will accelerate our product roadmap and expand our go-to-market team across Europe and Asia Pacific regions.",
    "Slack Connect message from partner TechBridge Consulting: Shared document link for the joint webinar presentation deck. The webinar is scheduled for May 15th covering best practices in CRM data migration. Expected attendance is around three hundred registered participants.",
    "Huddle recording saved in #design-team: Forty-five minute session reviewing the new onboarding flow wireframes. Participants: Anna Lee, Carlos Ruiz, Priya Sharma. Key decisions: simplified the sign-up form to three steps and added progress indicators throughout the flow.",
    "Automated alert in #infrastructure: Memory utilization on database replica node db-replica-03 exceeded eighty-five percent threshold. Auto-scaling policy triggered. Additional read replica provisioned. Current query load: 12,000 queries per second across the replica set.",
    "Channel message in #marketing from content lead Julia Watts: Blog post draft titled Five Strategies for Enterprise Data Governance submitted for review. Target publish date: next Monday. The post includes case studies from three customers who improved compliance scores by forty percent.",
    "Bot notification in #deploys: Canary deployment for recommendation-engine v2.8.1 detected elevated error rates. Error rate: 3.2 percent versus baseline of 0.4 percent. Automatic rollback initiated. Previous stable version v2.8.0 restored across all regions within four minutes.",
    "Shared file in #legal-reviews: Updated terms of service document version 4.1 uploaded by counsel Rebecca Foster. Changes include updated data processing addendum reflecting new privacy regulations and revised liability clauses for enterprise tier customers.",
    "Emoji reaction summary for poll in #team-social: Office event preferences. Happy hour: 34 votes. Board game night: 28 votes. Cooking class: 19 votes. Escape room: 22 votes. Happy hour wins. Event coordinator will book a venue for Friday the 25th.",
    "Status update in #incident-response: Incident INC-2847 post-mortem published. Root cause: expired TLS certificate on the payment gateway load balancer. Time to detection: eighteen minutes. Time to resolution: forty-two minutes. Action items assigned to prevent recurrence.",
    "Thread in #data-engineering from analyst Raj Patel: ETL pipeline for customer analytics warehouse completed nightly run. Processed 2.3 million rows. Three data quality checks flagged: duplicate customer IDs in the transactions table from the European region data feed.",
    "Notification in #hiring: New candidate submission for Senior Backend Engineer role. Candidate: Alex Kim. Source: employee referral from team lead Sarah Wong. Resume highlights: eight years experience with distributed systems, previous roles at two Fortune 500 companies.",
    "Channel post in #support-escalations: Priority one ticket from DataVault Corp regarding API rate limiting. Their integration is being throttled at 500 requests per minute but their contract specifies 2,000. Investigating whether the rate limit configuration was applied correctly.",
    "Workflow bot in #finance-ops: Monthly expense report aggregation complete. Total company spend: $847,000. Top categories: cloud infrastructure at $312,000, personnel travel at $89,000, software licenses at $156,000. Three expense reports still pending manager approval.",
    "Message in #random from developer Chris Lee: Found an interesting open source library called FastEmbed that could replace our current embedding pipeline. Benchmarks show forty percent faster inference with comparable accuracy. Sharing the GitHub link for the team to evaluate.",
]


def get_or_create_source(db, key: str, name: str) -> Source:
    source = db.scalar(select(Source).where(Source.key == key))
    if source:
        return source
    source = Source(key=key, name=name)
    db.add(source)
    db.flush()
    return source


def get_or_create_account(db, name: str) -> Account:
    account = db.scalar(select(Account).where(Account.name == name))
    if account:
        return account
    account = Account(name=name)
    db.add(account)
    db.flush()
    return account


def link_source_to_account(db, account: Account, source: Source):
    already_linked = db.scalar(
        select(account_sources.c.source_id).where(
            account_sources.c.account_id == account.id,
            account_sources.c.source_id == source.id,
        )
    )
    if not already_linked:
        account.sources.append(source)
        db.flush()


def main():
    db = SessionLocal()
    try:
        salesforce = get_or_create_source(db, "salesforce", "Salesforce")
        slack = get_or_create_source(db, "slack", "Slack")

        account_configs = [
            ("Acme Corp", [salesforce, slack]),
            ("Globex Inc", [salesforce]),
            ("Initech", [slack]),
            ("Umbrella Ltd", [salesforce, slack]),
        ]

        accounts_with_sources = []
        for name, sources in account_configs:
            account = get_or_create_account(db, name)
            for source in sources:
                link_source_to_account(db, account, source)
            accounts_with_sources.append((account, sources))

        db.commit()

        print(f"Sources: salesforce(id={salesforce.id}), slack(id={slack.id})")
        for acct, srcs in accounts_with_sources:
            src_names = ", ".join(s.name for s in srcs)
            print(f"Account: {acct.name}(id={acct.id}) -> [{src_names}]")

        queued_ids = []
        for i in range(200):
            account, sources = random.choice(accounts_with_sources)
            source = random.choice(sources)

            if source.key == "salesforce":
                payload = random.choice(SALESFORCE_PAYLOADS)
            else:
                payload = random.choice(SLACK_PAYLOADS)

            qer = QueuedEventRequest(
                account_id=account.id,
                source_id=source.id,
                payload=payload,
                status="queued",
            )
            db.add(qer)
            db.flush()
            queued_ids.append(qer.id)

        db.commit()
        print(f"\nCreated {len(queued_ids)} queued event requests.")

        print("Dispatching Celery tasks...")
        for qid in queued_ids:
            celery_app.send_task(
                "tasks.events.process_queued_event_request",
                args=[qid],
            )

        print("All tasks dispatched. The worker will process events, create summaries, and store embeddings.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
