import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL as string;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string;

export const isSupabaseConfigured = Boolean(
  supabaseUrl && supabaseUrl.startsWith('http') && supabaseAnonKey
);

if (!isSupabaseConfigured) {
  console.warn('Supabase env vars missing. Running in local/offline mode.');
}

// Fallback to valid URL structure so createClient doesn't throw during initialization when running offline
export const supabase = createClient(
  isSupabaseConfigured ? supabaseUrl : 'https://placeholder.supabase.co',
  isSupabaseConfigured ? supabaseAnonKey : 'placeholder-anon-key'
);

