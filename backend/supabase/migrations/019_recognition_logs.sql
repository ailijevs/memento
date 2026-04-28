-- Recognition analytics tables: track every detection attempt and successful match.

CREATE TABLE IF NOT EXISTS public.recognition_attempts (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    event_id uuid REFERENCES public.events(event_id) ON DELETE CASCADE,
    observer_user_id uuid REFERENCES auth.users(id),
    faces_detected integer DEFAULT 0,
    faces_matched integer DEFAULT 0,
    created_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.recognition_logs (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    event_id uuid REFERENCES public.events(event_id) ON DELETE CASCADE,
    recognized_user_id uuid REFERENCES auth.users(id),
    observer_user_id uuid REFERENCES auth.users(id),
    confidence double precision,
    created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_recog_attempts_event ON public.recognition_attempts(event_id);
CREATE INDEX IF NOT EXISTS idx_recog_attempts_created ON public.recognition_attempts(created_at);
CREATE INDEX IF NOT EXISTS idx_recog_logs_event ON public.recognition_logs(event_id);
CREATE INDEX IF NOT EXISTS idx_recog_logs_created ON public.recognition_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_recog_logs_recognized ON public.recognition_logs(recognized_user_id);
CREATE INDEX IF NOT EXISTS idx_recog_logs_observer ON public.recognition_logs(observer_user_id);
