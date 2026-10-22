-- StudyMind AI - Complete Supabase PostgreSQL Schema
-- Includes pgvector extension for source-grounded multimodal RAG and Bayesian Knowledge Tracing

-- 1. Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- 1b. Profiles Table (linked to Supabase Auth)
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name TEXT NOT NULL DEFAULT '',
    email TEXT,
    streak INTEGER NOT NULL DEFAULT 0,
    last_active TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE profiles ADD COLUMN IF NOT EXISTS email TEXT;

-- Auto-create profile on new user signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (id, full_name, email, streak, last_active, created_at)
  VALUES (
    NEW.id,
    COALESCE(NEW.raw_user_meta_data->>'full_name', ''),
    NEW.email,
    0,
    NOW(),
    NOW()
  )
  ON CONFLICT (id) DO NOTHING;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();

INSERT INTO public.profiles (id, full_name, email, streak, last_active, created_at)
SELECT id, COALESCE(raw_user_meta_data->>'full_name', ''), email, 0, NOW(), created_at
FROM auth.users
ON CONFLICT (id) DO NOTHING;

-- 2. Courses Table (owner_id links to auth user)
CREATE TABLE IF NOT EXISTS courses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    subject TEXT,
    semester TEXT,
    exam_date DATE,
    document_count INTEGER NOT NULL DEFAULT 0,
    topic_count INTEGER NOT NULL DEFAULT 0,
    concept_count INTEGER NOT NULL DEFAULT 0,
    overall_mastery FLOAT NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Course Units
CREATE TABLE IF NOT EXISTS course_units (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    course_id UUID REFERENCES courses(id) ON DELETE CASCADE,
    unit_number INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Documents & Media Files
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    course_id UUID REFERENCES courses(id) ON DELETE CASCADE,
    owner_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    file_hash TEXT,
    source_type TEXT,
    url TEXT,
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL, -- pdf, ppt, pptx, mp4, mp3, image
    file_size BIGINT,
    storage_path TEXT,
    status TEXT DEFAULT 'pending', -- pending, processing, processed, error
    page_count INTEGER DEFAULT 0,
    slide_count INTEGER DEFAULT 0,
    duration_seconds FLOAT DEFAULT 0.0,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE documents ADD COLUMN IF NOT EXISTS file_hash TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS source_type TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS url TEXT;
ALTER TABLE courses ADD COLUMN IF NOT EXISTS document_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE courses ADD COLUMN IF NOT EXISTS topic_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE courses ADD COLUMN IF NOT EXISTS concept_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE courses ADD COLUMN IF NOT EXISTS overall_mastery FLOAT NOT NULL DEFAULT 0;
CREATE UNIQUE INDEX IF NOT EXISTS documents_course_file_hash_unique ON documents(course_id, file_hash) WHERE file_hash IS NOT NULL;

-- 5. Topics
CREATE TABLE IF NOT EXISTS topics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    course_id UUID REFERENCES courses(id) ON DELETE CASCADE,
    unit_id UUID REFERENCES course_units(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    description TEXT,
    importance_weight FLOAT DEFAULT 1.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 6. Concepts
CREATE TABLE IF NOT EXISTS concepts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    course_id UUID REFERENCES courses(id) ON DELETE CASCADE,
    topic_id UUID REFERENCES topics(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    difficulty TEXT DEFAULT 'Medium', -- Easy, Medium, Hard
    initial_p_knowledge FLOAT DEFAULT 0.20,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 7. Concept Prerequisites (Dependency Graph)
CREATE TABLE IF NOT EXISTS concept_prerequisites (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    concept_id UUID REFERENCES concepts(id) ON DELETE CASCADE,
    prerequisite_id UUID REFERENCES concepts(id) ON DELETE CASCADE,
    relationship_strength FLOAT DEFAULT 1.0,
    reason TEXT,
    UNIQUE(concept_id, prerequisite_id)
);

ALTER TABLE concept_prerequisites ADD COLUMN IF NOT EXISTS reason TEXT;

-- 8. Visual Elements (Diagrams, Figures, Slides, Screenshots)
CREATE TABLE IF NOT EXISTS visual_elements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    course_id UUID REFERENCES courses(id) ON DELETE CASCADE,
    element_type TEXT NOT NULL, -- diagram, chart, table, figure, screenshot
    page_number INTEGER,
    slide_number INTEGER,
    image_url TEXT,
    caption TEXT,
    structured_description TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 9. Knowledge Chunks (Multimodal Source Units with Vector Embeddings)
CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    course_id UUID REFERENCES courses(id) ON DELETE CASCADE,
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    topic_id UUID REFERENCES topics(id) ON DELETE SET NULL,
    concept_id UUID REFERENCES concepts(id) ON DELETE SET NULL,
    source_type TEXT NOT NULL, -- pdf, slide, video, image
    url TEXT,
    document_name TEXT NOT NULL,
    page_number INTEGER,
    slide_number INTEGER,
    timestamp_start FLOAT,
    timestamp_end FLOAT,
    content TEXT NOT NULL,
    content_summary TEXT,
    visual_element_id UUID REFERENCES visual_elements(id) ON DELETE SET NULL,
    embedding vector(384), -- Supports cosine similarity vector indexing
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE knowledge_chunks ADD COLUMN IF NOT EXISTS url TEXT;

-- Vector index for cosine distance
CREATE INDEX IF NOT EXISTS knowledge_chunks_embedding_idx 
ON knowledge_chunks 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- 10. Conversations & Messages
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    course_id UUID REFERENCES courses(id) ON DELETE CASCADE,
    title TEXT DEFAULT 'Tutoring Session',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL, -- user, assistant
    content TEXT NOT NULL,
    mode TEXT DEFAULT 'Quick Explanation', -- Beginner, Exam Preparation, Deep Dive, Socratic Tutor, Practice Mode
    language TEXT DEFAULT 'en', -- en, hi, hinglish
    is_grounded BOOLEAN DEFAULT TRUE,
    citations JSONB DEFAULT '[]'::jsonb,
    is_outside_knowledge BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 11. Assessments & Questions
CREATE TABLE IF NOT EXISTS assessments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    course_id UUID REFERENCES courses(id) ON DELETE CASCADE,
    topic_id UUID REFERENCES topics(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    total_questions INTEGER DEFAULT 5,
    difficulty TEXT DEFAULT 'Adaptive',
    time_limit_minutes INTEGER DEFAULT 15,
    status TEXT DEFAULT 'pending', -- pending, in_progress, completed
    score FLOAT DEFAULT 0.0,
    last_report JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS questions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    course_id UUID REFERENCES courses(id) ON DELETE CASCADE,
    concept_id UUID REFERENCES concepts(id) ON DELETE SET NULL,
    question_text TEXT NOT NULL,
    question_type TEXT NOT NULL, -- mcq, short_answer, numerical, true_false, application
    difficulty TEXT NOT NULL, -- Easy, Medium, Hard
    options JSONB, -- Array of string options for MCQ
    correct_answer TEXT NOT NULL,
    explanation TEXT NOT NULL,
    source_document TEXT,
    source_location TEXT,
    source_chunk_id UUID REFERENCES knowledge_chunks(id) ON DELETE SET NULL,
    question_hash TEXT UNIQUE,
    verification_status TEXT DEFAULT 'verified', -- verified, needs_review, rejected
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS assessment_questions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    assessment_id UUID REFERENCES assessments(id) ON DELETE CASCADE,
    question_id UUID REFERENCES questions(id) ON DELETE CASCADE,
    sort_order INTEGER DEFAULT 1,
    student_answer TEXT,
    is_correct BOOLEAN,
    time_spent_seconds INTEGER DEFAULT 0,
    feedback TEXT,
    misconception TEXT
);

CREATE TABLE IF NOT EXISTS assessment_submissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    assessment_id UUID NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    score_percentage FLOAT NOT NULL,
    auto_submitted BOOLEAN DEFAULT FALSE,
    safe_mode_violation TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE assessments ADD COLUMN IF NOT EXISTS last_report JSONB;

-- One immutable answer event per question attempt, scoped to its student.
CREATE TABLE IF NOT EXISTS attempts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    concept_id UUID REFERENCES concepts(id) ON DELETE CASCADE,
    question_hash TEXT NOT NULL,
    correct BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, question_hash)
);

-- 12. Learner Mastery (Bayesian Knowledge Tracing - BKT)
CREATE TABLE IF NOT EXISTS learner_mastery (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id TEXT NOT NULL DEFAULT 'default_student', -- stores auth user UUID as text for backend compat
    course_id UUID REFERENCES courses(id) ON DELETE CASCADE,
    concept_id UUID REFERENCES concepts(id) ON DELETE CASCADE,
    mastery_probability FLOAT DEFAULT 0.20,
    confidence FLOAT DEFAULT 0.50,
    p_transit FLOAT DEFAULT 0.15,
    p_slip FLOAT DEFAULT 0.10,
    p_guess FLOAT DEFAULT 0.25,
    attempt_count INTEGER DEFAULT 0,
    correct_count INTEGER DEFAULT 0,
    incorrect_count INTEGER DEFAULT 0,
    last_attempt TIMESTAMP WITH TIME ZONE,
    last_review TIMESTAMP WITH TIME ZONE,
    UNIQUE(student_id, concept_id)
);

-- 13. Misconceptions
CREATE TABLE IF NOT EXISTS misconceptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id TEXT NOT NULL DEFAULT 'default_student', -- stores auth user UUID as text
    concept_id UUID REFERENCES concepts(id) ON DELETE CASCADE,
    misconception_title TEXT NOT NULL,
    evidence TEXT,
    status TEXT DEFAULT 'active', -- active, resolved
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 14. Revision Materials & Study Plans
CREATE TABLE IF NOT EXISTS revision_materials (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id TEXT,
    course_id UUID REFERENCES courses(id) ON DELETE CASCADE,
    topic_id UUID REFERENCES topics(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    summary TEXT,
    key_formulas JSONB DEFAULT '[]'::jsonb,
    flashcards JSONB DEFAULT '[]'::jsonb,
    common_mistakes JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE revision_materials ADD COLUMN IF NOT EXISTS student_id TEXT;

CREATE TABLE IF NOT EXISTS study_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id TEXT NOT NULL DEFAULT 'default_student',
    course_id UUID REFERENCES courses(id) ON DELETE CASCADE,
    exam_date DATE,
    daily_study_minutes INTEGER DEFAULT 60,
    schedule JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 15. Evaluation Benchmark & Results
CREATE TABLE IF NOT EXISTS evaluation_questions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    course_id UUID REFERENCES courses(id) ON DELETE CASCADE,
    question_type TEXT NOT NULL, -- source_answerable, multi_hop, visual, video, off_material, ambiguous
    question TEXT NOT NULL,
    expected_answer TEXT,
    source_document TEXT,
    source_location TEXT,
    expected_topic TEXT,
    is_answerable BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS evaluation_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    faithfulness FLOAT NOT NULL,
    answer_relevancy FLOAT NOT NULL,
    context_precision FLOAT NOT NULL,
    context_recall FLOAT NOT NULL,
    citation_accuracy FLOAT NOT NULL,
    unsupported_rate FLOAT NOT NULL,
    total_test_cases INTEGER NOT NULL,
    details JSONB DEFAULT '{}'::jsonb
);

-- ============================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================

-- Enable RLS on all user-scoped tables
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE courses ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE course_units ENABLE ROW LEVEL SECURITY;
ALTER TABLE visual_elements ENABLE ROW LEVEL SECURITY;
ALTER TABLE learner_mastery ENABLE ROW LEVEL SECURITY;
ALTER TABLE misconceptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE study_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE assessment_questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE assessment_submissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE revision_materials ENABLE ROW LEVEL SECURITY;

-- Keep this schema safe to reapply and remove permissive legacy demo policies.
DROP POLICY IF EXISTS "profiles_select_own" ON profiles;
DROP POLICY IF EXISTS "profiles_insert_own" ON profiles;
DROP POLICY IF EXISTS "profiles_update_own" ON profiles;
DROP POLICY IF EXISTS "courses_select_own" ON courses;
DROP POLICY IF EXISTS "courses_insert_own" ON courses;
DROP POLICY IF EXISTS "courses_update_own" ON courses;
DROP POLICY IF EXISTS "courses_delete_own" ON courses;
DROP POLICY IF EXISTS "documents_select_own" ON documents;
DROP POLICY IF EXISTS "documents_insert_own" ON documents;
DROP POLICY IF EXISTS "documents_delete_own" ON documents;
DROP POLICY IF EXISTS "documents_update_own" ON documents;
DROP POLICY IF EXISTS "course_units_owner_access" ON course_units;
DROP POLICY IF EXISTS "visual_elements_owner_access" ON visual_elements;
DROP POLICY IF EXISTS "mastery_select_own" ON learner_mastery;
DROP POLICY IF EXISTS "mastery_insert_own" ON learner_mastery;
DROP POLICY IF EXISTS "mastery_update_own" ON learner_mastery;
DROP POLICY IF EXISTS "misconceptions_select_own" ON misconceptions;
DROP POLICY IF EXISTS "misconceptions_insert_own" ON misconceptions;
DROP POLICY IF EXISTS "study_plans_select_own" ON study_plans;
DROP POLICY IF EXISTS "study_plans_insert_own" ON study_plans;
DROP POLICY IF EXISTS "study_plans_update_own" ON study_plans;
DROP POLICY IF EXISTS "attempts_select_own" ON attempts;
DROP POLICY IF EXISTS "attempts_insert_own" ON attempts;
DROP POLICY IF EXISTS "conversations_own" ON conversations;
DROP POLICY IF EXISTS "messages_own" ON messages;
DROP POLICY IF EXISTS "assessment_questions_own" ON assessment_questions;
DROP POLICY IF EXISTS "revision_materials_own" ON revision_materials;
DROP POLICY IF EXISTS "assessment_submissions_own" ON assessment_submissions;
DROP POLICY IF EXISTS "topics_public_read" ON topics;
DROP POLICY IF EXISTS "concepts_public_read" ON concepts;
DROP POLICY IF EXISTS "knowledge_chunks_public_read" ON knowledge_chunks;
DROP POLICY IF EXISTS "assessments_public_read" ON assessments;
DROP POLICY IF EXISTS "questions_public_read" ON questions;
DROP POLICY IF EXISTS "topics_owner_read" ON topics;
DROP POLICY IF EXISTS "concepts_owner_read" ON concepts;
DROP POLICY IF EXISTS "knowledge_chunks_owner_read" ON knowledge_chunks;
DROP POLICY IF EXISTS "assessments_owner_read" ON assessments;
DROP POLICY IF EXISTS "questions_owner_read" ON questions;

-- profiles: users can only read/write their own profile
CREATE POLICY "profiles_select_own" ON profiles FOR SELECT USING (auth.uid() = id);
CREATE POLICY "profiles_insert_own" ON profiles FOR INSERT WITH CHECK (auth.uid() = id);
CREATE POLICY "profiles_update_own" ON profiles FOR UPDATE USING (auth.uid() = id) WITH CHECK (auth.uid() = id);

-- courses: users can only access their own courses
CREATE POLICY "courses_select_own" ON courses FOR SELECT USING (auth.uid() = owner_id);
CREATE POLICY "courses_insert_own" ON courses FOR INSERT WITH CHECK (auth.uid() = owner_id);
CREATE POLICY "courses_update_own" ON courses FOR UPDATE USING (auth.uid() = owner_id) WITH CHECK (auth.uid() = owner_id);
CREATE POLICY "courses_delete_own" ON courses FOR DELETE USING (auth.uid() = owner_id);

-- documents: users can only access their own documents
CREATE POLICY "documents_select_own" ON documents FOR SELECT USING (auth.uid() = owner_id);
CREATE POLICY "documents_insert_own" ON documents FOR INSERT WITH CHECK (auth.uid() = owner_id);
CREATE POLICY "documents_update_own" ON documents FOR UPDATE USING (auth.uid() = owner_id) WITH CHECK (auth.uid() = owner_id);
CREATE POLICY "documents_delete_own" ON documents FOR DELETE USING (auth.uid() = owner_id);
CREATE POLICY "course_units_owner_access" ON course_units FOR ALL USING (EXISTS (SELECT 1 FROM courses c WHERE c.id = course_units.course_id AND c.owner_id = auth.uid())) WITH CHECK (EXISTS (SELECT 1 FROM courses c WHERE c.id = course_units.course_id AND c.owner_id = auth.uid()));
CREATE POLICY "visual_elements_owner_access" ON visual_elements FOR ALL USING (EXISTS (SELECT 1 FROM courses c WHERE c.id = visual_elements.course_id AND c.owner_id = auth.uid())) WITH CHECK (EXISTS (SELECT 1 FROM courses c WHERE c.id = visual_elements.course_id AND c.owner_id = auth.uid()));

-- learner_mastery: users can only access their own mastery records
CREATE POLICY "mastery_select_own" ON learner_mastery FOR SELECT USING (student_id = auth.uid()::text);
CREATE POLICY "mastery_insert_own" ON learner_mastery FOR INSERT WITH CHECK (student_id = auth.uid()::text);
CREATE POLICY "mastery_update_own" ON learner_mastery FOR UPDATE USING (student_id = auth.uid()::text) WITH CHECK (student_id = auth.uid()::text);

-- misconceptions: users can only access their own misconceptions
CREATE POLICY "misconceptions_select_own" ON misconceptions FOR SELECT USING (student_id = auth.uid()::text);
CREATE POLICY "misconceptions_insert_own" ON misconceptions FOR INSERT WITH CHECK (student_id = auth.uid()::text);

-- study_plans: users can only access their own study plans
CREATE POLICY "study_plans_select_own" ON study_plans FOR SELECT USING (student_id = auth.uid()::text);
CREATE POLICY "study_plans_insert_own" ON study_plans FOR INSERT WITH CHECK (student_id = auth.uid()::text);
CREATE POLICY "study_plans_update_own" ON study_plans FOR UPDATE USING (student_id = auth.uid()::text) WITH CHECK (student_id = auth.uid()::text);

CREATE POLICY "attempts_select_own" ON attempts FOR SELECT USING (user_id = auth.uid());
CREATE POLICY "attempts_insert_own" ON attempts FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY "conversations_own" ON conversations FOR ALL USING (EXISTS (SELECT 1 FROM courses c WHERE c.id = conversations.course_id AND c.owner_id = auth.uid())) WITH CHECK (EXISTS (SELECT 1 FROM courses c WHERE c.id = conversations.course_id AND c.owner_id = auth.uid()));
CREATE POLICY "messages_own" ON messages FOR ALL USING (EXISTS (SELECT 1 FROM conversations v JOIN courses c ON c.id = v.course_id WHERE v.id = messages.conversation_id AND c.owner_id = auth.uid())) WITH CHECK (EXISTS (SELECT 1 FROM conversations v JOIN courses c ON c.id = v.course_id WHERE v.id = messages.conversation_id AND c.owner_id = auth.uid()));
CREATE POLICY "assessment_questions_own" ON assessment_questions FOR ALL USING (EXISTS (SELECT 1 FROM assessments a JOIN courses c ON c.id = a.course_id WHERE a.id = assessment_questions.assessment_id AND c.owner_id = auth.uid())) WITH CHECK (EXISTS (SELECT 1 FROM assessments a JOIN courses c ON c.id = a.course_id WHERE a.id = assessment_questions.assessment_id AND c.owner_id = auth.uid()));
CREATE POLICY "assessment_submissions_own" ON assessment_submissions FOR ALL USING (student_id = auth.uid()) WITH CHECK (student_id = auth.uid());
CREATE POLICY "revision_materials_own" ON revision_materials FOR ALL USING (EXISTS (SELECT 1 FROM courses c WHERE c.id = revision_materials.course_id AND c.owner_id = auth.uid())) WITH CHECK (EXISTS (SELECT 1 FROM courses c WHERE c.id = revision_materials.course_id AND c.owner_id = auth.uid()));

-- Public read access for shared tables (concepts, topics, knowledge_chunks, etc.)
ALTER TABLE topics ENABLE ROW LEVEL SECURITY;
ALTER TABLE concepts ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE questions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "topics_owner_read" ON topics FOR SELECT USING (EXISTS (SELECT 1 FROM courses c WHERE c.id = topics.course_id AND c.owner_id = auth.uid()));
CREATE POLICY "concepts_owner_read" ON concepts FOR SELECT USING (EXISTS (SELECT 1 FROM courses c WHERE c.id = concepts.course_id AND c.owner_id = auth.uid()));
CREATE POLICY "knowledge_chunks_owner_read" ON knowledge_chunks FOR SELECT USING (EXISTS (SELECT 1 FROM documents d WHERE d.id = knowledge_chunks.document_id AND d.owner_id = auth.uid()));
CREATE POLICY "assessments_owner_read" ON assessments FOR SELECT USING (EXISTS (SELECT 1 FROM courses c WHERE c.id = assessments.course_id AND c.owner_id = auth.uid()));
-- Questions are served through the authenticated API, which removes answer keys before a quiz.
