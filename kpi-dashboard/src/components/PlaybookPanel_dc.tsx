/**
 * Data Center Playbook Panel Component
 * Displays recommended playbooks for DC tenants
 */

import React, { useState, useEffect } from 'react';
import { BookOpen, Play, CheckCircle, Clock } from 'lucide-react';

interface Playbook {
  recommendation_id: string;
  playbook_id: string;
  playbook_name: string;
  description: string;
  priority: 'critical' | 'high' | 'medium' | 'low';
  action_items: string[];
}

interface PlaybookPanelProps {
  tenantId: number | null;
}

const PlaybookPanel_dc: React.FC<PlaybookPanelProps> = ({ tenantId }) => {
  const [playbooks, setPlaybooks] = useState<Playbook[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (tenantId) {
      loadPlaybooks();
    }
  }, [tenantId]);

  const loadPlaybooks = async () => {
    if (!tenantId) return;
    
    setLoading(true);
    try {
      const response = await fetch(`/api/dc/recommendations/${tenantId}`, {
        credentials: 'include',
      });

      if (response.ok) {
        const data = await response.json();
        setPlaybooks(data.recommendations || []);
      }
    } catch (error) {
      console.error('Error loading playbooks:', error);
    } finally {
      setLoading(false);
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'critical':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'high':
        return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'low':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="space-y-3">
            <div className="h-24 bg-gray-200 rounded"></div>
            <div className="h-24 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (!tenantId) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="text-center py-12">
          <BookOpen className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-500">Select a tenant to view recommended playbooks</p>
        </div>
      </div>
    );
  }

  if (playbooks.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="text-center py-12">
          <CheckCircle className="h-12 w-12 text-green-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No CS AI Agents Recommended</h3>
          <p className="text-gray-500">All systems are operating within normal parameters.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Recommended CS AI Agents</h2>
          <p className="text-sm text-gray-500 mt-1">{playbooks.length} recommendations available</p>
        </div>
        <BookOpen className="h-6 w-6 text-blue-600" />
      </div>

      <div className="space-y-4">
        {playbooks.map((playbook) => (
          <div
            key={playbook.recommendation_id}
            className="border rounded-lg p-4 hover:shadow-md transition-shadow"
          >
            <div className="flex items-start justify-between mb-3">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <h3 className="font-semibold text-gray-900">{playbook.playbook_name}</h3>
                  <span className={`px-2 py-1 text-xs font-medium rounded border ${getPriorityColor(playbook.priority)}`}>
                    {playbook.priority}
                  </span>
                </div>
                <p className="text-sm text-gray-600">{playbook.description}</p>
              </div>
              <button className="ml-4 p-2 text-blue-600 hover:bg-blue-50 rounded">
                <Play className="h-5 w-5" />
              </button>
            </div>

            {playbook.action_items && playbook.action_items.length > 0 && (
              <div className="mt-3 pt-3 border-t border-gray-200">
                <p className="text-xs font-medium text-gray-700 mb-2">Action Items:</p>
                <ul className="space-y-1">
                  {playbook.action_items.map((item, index) => (
                    <li key={index} className="flex items-start gap-2 text-sm text-gray-600">
                      <Clock className="h-4 w-4 mt-0.5 text-gray-400" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default PlaybookPanel_dc;

