import React, { useState, useEffect } from 'react';
import ResumeUploader from './ResumeUploader';
import RepoConnect from './RepoConnect';
import SkillEvidenceViewer from './SkillEvidenceViewer';
import QuizConfigurator from './QuizConfigurator';
import QuizRunner from './QuizRunner';
import QuizResults from './QuizResults';
import PracticeHistory from './PracticeHistory';
import { practiceApi } from '../../services/practiceApi';

export default function CandidateDashboard() {
  const [activeTab, setActiveTab] = useState('practice'); // 'practice', 'resume', 'repos', 'evidence', 'history'
  const [skills, setSkills] = useState([]);
  const [repos, setRepos] = useState([]);
  const [selectedRepo, setSelectedRepo] = useState(null);

  // Active quiz session state
  const [activeQuiz, setActiveQuiz] = useState(null);
  const [quizResults, setQuizResults] = useState(null);

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      const [skillsData, reposData] = await Promise.all([
        practiceApi.getSkills(),
        practiceApi.getRepositories()
      ]);
      setSkills(skillsData || []);
      setRepos(reposData || []);
      if (reposData?.length > 0) {
        setSelectedRepo(reposData[0]);
      }
    } catch (err) {
      console.error('Failed to load initial candidate data:', err);
    }
  };

  const handleQuizStarted = (quizPayload) => {
    setActiveQuiz(quizPayload);
    setQuizResults(null);
    setActiveTab('practice');
  };

  const handleQuizCompleted = (resultsPayload) => {
    setQuizResults(resultsPayload);
    setActiveQuiz(null);
    setActiveTab('practice');
  };

  const handlePracticeAgain = () => {
    setActiveQuiz(null);
    setQuizResults(null);
    setActiveTab('practice');
  };

  const handleReviewPastQuiz = async (quizId) => {
    try {
      const results = await practiceApi.getQuizResults(quizId);
      setQuizResults(results);
      setActiveQuiz(null);
      setActiveTab('practice');
    } catch (err) {
      console.error('Failed to load quiz results:', err);
    }
  };

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '24px 20px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Top Banner */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(24, 24, 27, 0.8) 0%, rgba(9, 9, 11, 0.95) 100%)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-lg)',
        padding: '24px 28px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '16px'
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <span style={{ fontSize: '11px', fontWeight: 700, padding: '2px 8px', borderRadius: '4px', background: 'var(--blue-dim)', color: 'var(--blue)', textTransform: 'uppercase' }}>
              Phase 2: Candidate Practice
            </span>
            <span style={{ fontSize: '12px', color: 'var(--text-dim)' }}>•</span>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Personalized Technical Assessment</span>
          </div>
          <h1 style={{ fontSize: '22px', fontWeight: 700, color: 'var(--text-primary)' }}>
            Candidate Practice & Skill Intelligence
          </h1>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '4px' }}>
            Upload your resume, connect your GitHub repositories, verify code evidence, and test your engineering depth with objective AI quizzes.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '16px' }}>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '18px', fontWeight: 700, color: 'var(--text-primary)' }}>
              {skills.length}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Reviewed Skills</div>
          </div>
          <div style={{ width: '1px', background: 'var(--border)' }} />
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '18px', fontWeight: 700, color: 'var(--text-primary)' }}>
              {repos.length}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Connected Repos</div>
          </div>
        </div>
      </div>

      {/* Sub-Navigation Tabs */}
      <div style={{
        display: 'flex',
        gap: '8px',
        borderBottom: '1px solid var(--border)',
        paddingBottom: '8px',
        overflowX: 'auto'
      }}>
        {[
          { id: 'practice', label: '🎯 Practice Quizzes' },
          { id: 'resume', label: '📄 Resume & Skills' },
          { id: 'repos', label: '🐙 Repositories' },
          { id: 'evidence', label: '🔍 Code Evidence' },
          { id: 'history', label: '📈 Progress & History' },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              padding: '8px 16px',
              borderRadius: 'var(--radius-sm)',
              border: `1px solid ${activeTab === tab.id ? 'var(--border-hover)' : 'transparent'}`,
              background: activeTab === tab.id ? 'var(--bg-elevated)' : 'transparent',
              color: activeTab === tab.id ? 'var(--text-primary)' : 'var(--text-muted)',
              fontSize: '13px',
              fontWeight: activeTab === tab.id ? 600 : 400,
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              transition: 'all 0.15s ease'
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Panels */}
      <div>
        {activeTab === 'practice' && (
          <div>
            {activeQuiz ? (
              <QuizRunner
                quiz={activeQuiz}
                onQuizCompleted={handleQuizCompleted}
                onCancel={() => setActiveQuiz(null)}
              />
            ) : quizResults ? (
              <QuizResults
                results={quizResults}
                onPracticeAgain={handlePracticeAgain}
                onBackToDashboard={() => setQuizResults(null)}
              />
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                <QuizConfigurator
                  skills={skills}
                  repos={repos}
                  onQuizStarted={handleQuizStarted}
                />
              </div>
            )}
          </div>
        )}

        {activeTab === 'resume' && (
          <ResumeUploader
            onSkillsUpdated={(updated) => setSkills(updated)}
          />
        )}

        {activeTab === 'repos' && (
          <RepoConnect
            selectedRepoId={selectedRepo?.id}
            onSelectRepo={(r) => {
              setSelectedRepo(r);
              setActiveTab('evidence');
            }}
          />
        )}

        {activeTab === 'evidence' && (
          <SkillEvidenceViewer
            repoId={selectedRepo?.id}
            repoName={selectedRepo?.display_name}
          />
        )}

        {activeTab === 'history' && (
          <PracticeHistory
            onReviewQuiz={handleReviewPastQuiz}
          />
        )}
      </div>
    </div>
  );
}
