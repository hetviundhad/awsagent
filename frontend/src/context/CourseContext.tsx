import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { Course } from '../types';
import { api } from '../services/api';
import { useAuth } from './AuthContext';

interface CourseContextValue {
  activeCourseId: string;
  activeCourse: Course | null;
  courses: Course[];
  loading: boolean;
  selectCourse: (id: string) => void;
  refreshCourses: () => Promise<Course[]>;
}

const CourseContext = createContext<CourseContextValue | null>(null);

export const CourseProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user } = useAuth();
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  // Initialize activeCourseId immediately from localStorage
  const [activeCourseId, setActiveCourseIdState] = useState<string>(() => {
    return localStorage.getItem('studymind_active_course') || '';
  });

  const getUserCourseKey = useCallback(() => {
    return user?.id ? `studymind_active_course_${user.id}` : 'studymind_active_course';
  }, [user]);

  const selectCourse = useCallback((id: string) => {
    setActiveCourseIdState(id);
    const key = getUserCourseKey();
    if (id) {
      localStorage.setItem(key, id);
      localStorage.setItem('studymind_active_course', id);
    } else {
      localStorage.removeItem(key);
      localStorage.removeItem('studymind_active_course');
    }
  }, [getUserCourseKey]);

  const refreshCourses = useCallback(async (): Promise<Course[]> => {
    try {
      setLoading(true);
      const data = await api.getCourses();
      setCourses(data);

      if (data && data.length > 0) {
        const userKey = getUserCourseKey();
        const savedId = localStorage.getItem(userKey) || localStorage.getItem('studymind_active_course');
        const matched = savedId ? data.find((c: Course) => c.id === savedId) : null;
        const targetId = matched ? matched.id : data[0].id;
        setActiveCourseIdState(targetId);
        localStorage.setItem(userKey, targetId);
        localStorage.setItem('studymind_active_course', targetId);
      } else {
        setActiveCourseIdState('');
      }
      return data;
    } catch (err) {
      console.error('Failed to load courses in CourseContext:', err);
      return [];
    } finally {
      setLoading(false);
    }
  }, [getUserCourseKey]);

  useEffect(() => {
    refreshCourses();
  }, [refreshCourses]);

  const activeCourse = courses.find((c) => c.id === activeCourseId) || null;

  return (
    <CourseContext.Provider
      value={{
        activeCourseId,
        activeCourse,
        courses,
        loading,
        selectCourse,
        refreshCourses,
      }}
    >
      {children}
    </CourseContext.Provider>
  );
};

export const useCourse = (): CourseContextValue => {
  const ctx = useContext(CourseContext);
  if (!ctx) {
    throw new Error('useCourse must be used within a CourseProvider');
  }
  return ctx;
};
