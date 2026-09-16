ROLE_USER = "USER"
ROLE_TECHNICIAN = "TECHNICIAN"
ROLE_REVIEWER = "REVIEWER"
ROLE_ADMIN = "ADMIN"

VALID_USER_ROLES = {ROLE_USER, ROLE_TECHNICIAN, ROLE_REVIEWER, ROLE_ADMIN}

# Running orchestrations (LLM planning, executing Agent Skills, follow-up
# questions) on requests you own. Everyone except REVIEWER: a reviewer's job
# is to evaluate what was produced, not to produce it (separation of duties).
ORCHESTRATION_ROLES = {ROLE_USER, ROLE_TECHNICIAN, ROLE_ADMIN}

# Curating which Agent Skills exist in the catalog (create/import a
# manifest). Narrower than ORCHESTRATION_ROLES: running an existing,
# already-vetted skill is a different trust level from deciding what skills
# the whole ecosystem can run.
SKILL_CATALOG_ROLES = {ROLE_TECHNICIAN, ROLE_ADMIN}

HUMAN_REVIEW_ROLES = {ROLE_REVIEWER, ROLE_ADMIN}
