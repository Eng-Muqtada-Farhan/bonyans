"""initial_schema

Revision ID: 313fab49d281
Revises: 
Create Date: 2026-08-29 18:46:40.240503

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '313fab49d281'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the full Bunyan schema from scratch."""
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS companies (
            id                        SERIAL PRIMARY KEY,
            name                      TEXT NOT NULL,
            city                      TEXT NOT NULL,
            phone                     TEXT NOT NULL,
            spec                      TEXT NOT NULL,
            description               TEXT,
            email                     TEXT,
            website                   TEXT,
            map_link                  TEXT,
            rating                    DOUBLE PRECISION NOT NULL DEFAULT 5,
            verified                  INTEGER NOT NULL DEFAULT 0,
            status                    TEXT NOT NULL DEFAULT 'pending',
            created_at                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            image_url                 TEXT,
            verification_status       TEXT NOT NULL DEFAULT 'pending',
            owner_user_id             INTEGER,
            slug                      TEXT,
            country                   TEXT NOT NULL DEFAULT 'IQ',
            cover_url                 TEXT,
            facebook_url             TEXT,
            instagram_url             TEXT,
            linkedin_url             TEXT,
            subscription_plan         TEXT NOT NULL DEFAULT 'free',
            subscription_expires_at   TIMESTAMPTZ,
            updated_at                TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS company_users (
            id            SERIAL PRIMARY KEY,
            company_id    INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            email         TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            provider      TEXT NOT NULL DEFAULT 'email',
            provider_id   TEXT,
            is_active     BOOLEAN NOT NULL DEFAULT TRUE,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_company_users_company_id ON company_users(company_id);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS company_projects (
            id              SERIAL PRIMARY KEY,
            company_id      INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            title           TEXT NOT NULL,
            description     TEXT,
            location        TEXT,
            completion_date TEXT,
            image_url       TEXT,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_company_projects_company_id ON company_projects(company_id);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS company_gallery (
            id          SERIAL PRIMARY KEY,
            company_id  INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            project_id  INTEGER REFERENCES company_projects(id) ON DELETE CASCADE,
            image_url   TEXT NOT NULL,
            title       TEXT,
            stage       TEXT,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_company_gallery_company_id ON company_gallery(company_id);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS company_views (
            id          SERIAL PRIMARY KEY,
            company_id  INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            ip_hash     TEXT,
            user_agent  TEXT,
            viewed_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_company_views_company_id ON company_views(company_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_company_views_viewed_at ON company_views(viewed_at);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id                SERIAL PRIMARY KEY,
            email             TEXT UNIQUE NOT NULL,
            phone             TEXT,
            display_name      TEXT,
            avatar_url        TEXT,
            provider          TEXT NOT NULL DEFAULT 'email',
            provider_id       TEXT,
            password_hash     TEXT,
            is_email_verified BOOLEAN NOT NULL DEFAULT FALSE,
            is_phone_verified BOOLEAN NOT NULL DEFAULT FALSE,
            is_active         BOOLEAN NOT NULL DEFAULT TRUE,
            created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_provider_id ON users(provider, provider_id) WHERE provider_id IS NOT NULL;")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS company_members (
            id         SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            role       TEXT NOT NULL DEFAULT 'owner',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (company_id, user_id)
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_company_members_company_id ON company_members(company_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_company_members_user_id ON company_members(user_id);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS project_requests (
            id            SERIAL PRIMARY KEY,
            customer_name TEXT NOT NULL,
            phone         TEXT NOT NULL,
            email         TEXT,
            city          TEXT NOT NULL,
            project_type  TEXT NOT NULL,
            description   TEXT,
            budget        TEXT,
            status        TEXT NOT NULL DEFAULT 'open',
            company_id    INTEGER REFERENCES companies(id) ON DELETE SET NULL,
            user_id       INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_project_requests_company_id ON project_requests(company_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_project_requests_status ON project_requests(status);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_project_requests_created_at ON project_requests(created_at DESC);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS projects (
            id            SERIAL PRIMARY KEY,
            title         TEXT NOT NULL,
            category      TEXT NOT NULL,
            city          TEXT NOT NULL,
            country       TEXT NOT NULL DEFAULT 'IQ',
            budget_min    NUMERIC,
            budget_max    NUMERIC,
            description   TEXT,
            attachments   TEXT NOT NULL DEFAULT '[]',
            contact_name  TEXT NOT NULL,
            contact_phone TEXT NOT NULL,
            contact_email TEXT,
            status        TEXT NOT NULL DEFAULT 'pending',
            owner_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_projects_city ON projects(city);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_projects_category ON projects(category);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_projects_owner ON projects(owner_user_id) WHERE owner_user_id IS NOT NULL;")
    op.execute("CREATE INDEX IF NOT EXISTS idx_projects_created_at ON projects(created_at DESC);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS project_bids (
            id            SERIAL PRIMARY KEY,
            project_id    INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            company_id    INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            price         NUMERIC NOT NULL,
            duration_days INTEGER,
            message       TEXT,
            status        TEXT NOT NULL DEFAULT 'submitted',
            created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (project_id, company_id)
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_bids_project_id ON project_bids(project_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_bids_company_id ON project_bids(company_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_bids_status ON project_bids(status);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS subscription_plans (
            id                SERIAL PRIMARY KEY,
            code              TEXT UNIQUE NOT NULL,
            name              TEXT NOT NULL,
            monthly_price     NUMERIC NOT NULL DEFAULT 0,
            yearly_price      NUMERIC NOT NULL DEFAULT 0,
            max_images        INTEGER NOT NULL DEFAULT 3,
            max_project_leads INTEGER NOT NULL DEFAULT 1,
            search_priority   INTEGER NOT NULL DEFAULT 0,
            is_verified       BOOLEAN NOT NULL DEFAULT FALSE,
            is_featured       BOOLEAN NOT NULL DEFAULT FALSE,
            created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_sub_plans_code ON subscription_plans(code);")
    op.execute(
        """
        INSERT INTO subscription_plans (code, name, monthly_price, yearly_price, max_images, max_project_leads, search_priority, is_verified, is_featured)
        VALUES
            ('starter', 'STARTER', 0, 0, 3, 1, 0, FALSE, FALSE),
            ('active', 'ACTIVE', 10, 100, 15, 5, 1, FALSE, FALSE),
            ('featured', 'FEATURED', 20, 200, 50, 20, 2, TRUE, TRUE),
            ('partner', 'PARTNER', 40, 400, -1, -1, 3, TRUE, TRUE)
        ON CONFLICT (code) DO NOTHING;
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS subscription_requests (
            id           SERIAL PRIMARY KEY,
            company_id   INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            plan_id      INTEGER NOT NULL REFERENCES subscription_plans(id),
            status       TEXT NOT NULL DEFAULT 'pending',
            notes        TEXT,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            processed_at TIMESTAMPTZ,
            processed_by TEXT
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_sub_req_company_id ON subscription_requests(company_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_sub_req_status ON subscription_requests(status);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS company_subscriptions (
            id          SERIAL PRIMARY KEY,
            company_id  INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            plan_id     INTEGER NOT NULL REFERENCES subscription_plans(id),
            status      TEXT NOT NULL DEFAULT 'active',
            is_founder  BOOLEAN NOT NULL DEFAULT FALSE,
            start_date  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            expires_at  TIMESTAMPTZ,
            auto_renew  BOOLEAN NOT NULL DEFAULT FALSE,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_company_subs_company_id ON company_subscriptions(company_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_company_subs_status ON company_subscriptions(status);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_company_subs_expires ON company_subscriptions(expires_at) WHERE expires_at IS NOT NULL;")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id             SERIAL PRIMARY KEY,
            project_id     INTEGER REFERENCES projects(id) ON DELETE SET NULL,
            client_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            company_id     INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_conv_client ON conversations(client_user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_conv_company ON conversations(company_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_conv_project ON conversations(project_id) WHERE project_id IS NOT NULL;")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_messages (
            id              SERIAL PRIMARY KEY,
            conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            sender_type     TEXT NOT NULL,
            sender_id       INTEGER NOT NULL,
            message         TEXT NOT NULL,
            is_read         BOOLEAN NOT NULL DEFAULT FALSE,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_msg_conv ON chat_messages(conversation_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_msg_read ON chat_messages(is_read) WHERE is_read = FALSE;")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS notifications (
            id         SERIAL PRIMARY KEY,
            user_id    INTEGER REFERENCES users(id) ON DELETE CASCADE,
            company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
            type       TEXT NOT NULL,
            title      TEXT NOT NULL,
            message    TEXT NOT NULL,
            is_read    BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_notif_user ON notifications(user_id) WHERE user_id IS NOT NULL;")
    op.execute("CREATE INDEX IF NOT EXISTS idx_notif_company ON notifications(company_id) WHERE company_id IS NOT NULL;")
    op.execute("CREATE INDEX IF NOT EXISTS idx_notif_unread ON notifications(is_read) WHERE is_read = FALSE;")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS reviews (
            id          SERIAL PRIMARY KEY,
            company_id  INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            client_name TEXT NOT NULL,
            project_id  INTEGER REFERENCES projects(id) ON DELETE SET NULL,
            rating      INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
            comment     TEXT,
            status      TEXT NOT NULL DEFAULT 'pending',
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_reviews_project ON reviews(project_id) WHERE project_id IS NOT NULL;")
    op.execute("CREATE INDEX IF NOT EXISTS idx_reviews_company ON reviews(company_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_reviews_status ON reviews(status);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS review_replies (
            id         SERIAL PRIMARY KEY,
            review_id  INTEGER NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
            company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            reply      TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_reply_review ON review_replies(review_id);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS activity_log (
            id         SERIAL PRIMARY KEY,
            company_id INTEGER REFERENCES companies(id) ON DELETE SET NULL,
            user_id    INTEGER REFERENCES users(id) ON DELETE SET NULL,
            action     TEXT NOT NULL,
            metadata   TEXT NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_activity_company ON activity_log(company_id) WHERE company_id IS NOT NULL;")
    op.execute("CREATE INDEX IF NOT EXISTS idx_activity_user ON activity_log(user_id) WHERE user_id IS NOT NULL;")
    op.execute("CREATE INDEX IF NOT EXISTS idx_activity_created ON activity_log(created_at DESC);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS security_audit_log (
            id         SERIAL PRIMARY KEY,
            actor_type TEXT NOT NULL,
            actor_id   TEXT NOT NULL DEFAULT '',
            action     TEXT NOT NULL,
            ip_hash    TEXT NOT NULL DEFAULT '',
            user_agent TEXT NOT NULL DEFAULT '',
            meta       TEXT NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_action ON security_audit_log(action);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_created ON security_audit_log(created_at DESC);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_actor ON security_audit_log(actor_type, actor_id);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS categories (
            id         SERIAL PRIMARY KEY,
            name_ar    TEXT NOT NULL UNIQUE,
            name_en    TEXT NOT NULL DEFAULT '',
            icon       TEXT NOT NULL DEFAULT '🏗',
            is_active  BOOLEAN NOT NULL DEFAULT TRUE,
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute(
        """
        INSERT INTO categories (name_ar, name_en, icon, is_active, sort_order)
        VALUES
            ('مقاولات عامة', 'General Contracting', '🏗', TRUE, 1),
            ('تصميم واستشارات هندسية', 'Design & Engineering Consulting', '📐', TRUE, 2),
            ('فحص تربة ومساحة', 'Soil Testing & Surveying', '🔬', TRUE, 3),
            ('حفر وتجهيز مواقع', 'Excavation & Site Preparation', '🚜', TRUE, 4),
            ('كهرباء وإنارة', 'Electrical & Lighting', '⚡', TRUE, 5),
            ('أعمال صحية وسباكة', 'Plumbing & Sanitary Works', '🔧', TRUE, 6),
            ('عزل مائي وحراري', 'Waterproofing & Insulation', '🛡', TRUE, 7),
            ('تشطيبات وأصباغ', 'Finishing & Painting', '🎨', TRUE, 8),
            ('حديد وحدادة', 'Ironwork & Metalwork', '⚙️', TRUE, 9),
            ('نجارة وأعمال خشبية', 'Carpentry & Woodwork', '🪵', TRUE, 10),
            ('ألمنيوم وواجهات زجاجية', 'Aluminum & Glass Facades', '🏢', TRUE, 11),
            ('ديكور داخلي وجبس', 'Interior Decor & Plaster', '✨', TRUE, 12),
            ('تنسيق حدائق وشلالات', 'Landscaping & Water Features', '🌿', TRUE, 13),
            ('تبريد وتكييف', 'HVAC', '❄️', TRUE, 14),
            ('مصاعد وسلالم متحركة', 'Elevators & Escalators', '🛗', TRUE, 15),
            ('أنظمة حريق وسلامة', 'Fire & Safety Systems', '🔥', TRUE, 16),
            ('أنظمة مراقبة وأمن ذكي', 'Smart Security & Surveillance', '📷', TRUE, 17),
            ('طاقة شمسية ومتجددة', 'Solar & Renewable Energy', '☀️', TRUE, 18),
            ('طرق وجسور وبنية تحتية', 'Roads, Bridges & Infrastructure', '🛣', TRUE, 19),
            ('تأجير آليات ومعدات ثقيلة', 'Heavy Equipment Rental', '🏗️', TRUE, 20),
            ('توريد مواد بناء أساسية', 'Basic Building Materials Supply', '🧱', TRUE, 21),
            ('توريد سيراميك وأدوات صحية', 'Ceramics & Sanitary Ware Supply', '🚿', TRUE, 22)
        ON CONFLICT (name_ar) DO NOTHING;
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS whatsapp_clicks (
            id         SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            ip_hash    TEXT NOT NULL DEFAULT '',
            clicked_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )

    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_companies_slug ON companies(slug) WHERE slug IS NOT NULL;")
    op.execute("CREATE INDEX IF NOT EXISTS idx_companies_owner_user_id ON companies(owner_user_id) WHERE owner_user_id IS NOT NULL;")
    op.execute("CREATE INDEX IF NOT EXISTS idx_companies_subscription_plan ON companies(subscription_plan);")


def downgrade() -> None:
    """Drop the full Bunyan schema."""
    op.execute("DROP TABLE IF EXISTS whatsapp_clicks CASCADE;")
    op.execute("DROP TABLE IF EXISTS categories CASCADE;")
    op.execute("DROP TABLE IF EXISTS security_audit_log CASCADE;")
    op.execute("DROP TABLE IF EXISTS activity_log CASCADE;")
    op.execute("DROP TABLE IF EXISTS review_replies CASCADE;")
    op.execute("DROP TABLE IF EXISTS reviews CASCADE;")
    op.execute("DROP TABLE IF EXISTS notifications CASCADE;")
    op.execute("DROP TABLE IF EXISTS chat_messages CASCADE;")
    op.execute("DROP TABLE IF EXISTS conversations CASCADE;")
    op.execute("DROP TABLE IF EXISTS company_subscriptions CASCADE;")
    op.execute("DROP TABLE IF EXISTS subscription_requests CASCADE;")
    op.execute("DROP TABLE IF EXISTS subscription_plans CASCADE;")
    op.execute("DROP TABLE IF EXISTS project_bids CASCADE;")
    op.execute("DROP TABLE IF EXISTS projects CASCADE;")
    op.execute("DROP TABLE IF EXISTS project_requests CASCADE;")
    op.execute("DROP TABLE IF EXISTS company_members CASCADE;")
    op.execute("DROP TABLE IF EXISTS users CASCADE;")
    op.execute("DROP TABLE IF EXISTS company_views CASCADE;")
    op.execute("DROP TABLE IF EXISTS company_gallery CASCADE;")
    op.execute("DROP TABLE IF EXISTS company_projects CASCADE;")
    op.execute("DROP TABLE IF EXISTS company_users CASCADE;")
    op.execute("DROP TABLE IF EXISTS companies CASCADE;")
