/**
 * StakeholderMap.tsx
 * ==================
 * Grid of stakeholder cards from context graph STAKEHOLDER nodes.
 * Shows name, role badge, influence score, engagement, and revenue impact.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  RefreshCw,
  AlertTriangle,
  Users,
  Briefcase,
  TrendingUp,
  Mail,
} from 'lucide-react';
import { fetchGraphNodes, fmtDollar } from '../../../utils/contextGraphApi';
import type { ContextNodeDTO } from '../../../types/contextGraph';

interface StakeholderMapProps {
  accountId: number;
}

const ROLE_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  champion:        { bg: 'bg-green-100', text: 'text-green-800', label: 'Champion' },
  detractor:       { bg: 'bg-red-100',   text: 'text-red-800',   label: 'Detractor' },
  exec_sponsor:    { bg: 'bg-blue-100',  text: 'text-blue-800',  label: 'Exec Sponsor' },
  decision_maker:  { bg: 'bg-purple-100', text: 'text-purple-800', label: 'Decision Maker' },
  technical_lead:  { bg: 'bg-gray-100',  text: 'text-gray-800',  label: 'Technical Lead' },
  end_user:        { bg: 'bg-amber-100', text: 'text-amber-800', label: 'End User' },
  influencer:      { bg: 'bg-indigo-100', text: 'text-indigo-800', label: 'Influencer' },
};

const ENGAGEMENT_STYLES: Record<string, { bg: string; text: string }> = {
  daily:   { bg: 'bg-green-50',  text: 'text-green-700' },
  weekly:  { bg: 'bg-blue-50',   text: 'text-blue-700' },
  monthly: { bg: 'bg-amber-50',  text: 'text-amber-700' },
  quarterly: { bg: 'bg-gray-50', text: 'text-gray-700' },
};

const StakeholderMap: React.FC<StakeholderMapProps> = ({ accountId }) => {
  const [stakeholders, setStakeholders] = useState<ContextNodeDTO[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchGraphNodes(accountId, 'STAKEHOLDER', undefined, 50);
      setStakeholders(res.nodes || []);
    } catch (err: any) {
      setError(err.message || 'Failed to load stakeholders');
    } finally {
      setLoading(false);
    }
  }, [accountId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <AlertTriangle className="w-8 h-8 text-yellow-500 mx-auto mb-2" />
        <p className="text-gray-600">{error}</p>
      </div>
    );
  }

  if (stakeholders.length === 0) {
    return (
      <div className="text-center py-16">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-gray-100 mb-4">
          <Users className="w-7 h-7 text-gray-400" />
        </div>
        <h3 className="text-lg font-medium text-gray-700 mb-1">No Stakeholders Found</h3>
        <p className="text-sm text-gray-500 max-w-md mx-auto">
          No stakeholder nodes exist for this account in the context graph.
          Upload stakeholder data or run the context graph generator.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700">
          {stakeholders.length} Stakeholder{stakeholders.length !== 1 ? 's' : ''}
        </h3>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {stakeholders.map((sh) => {
          const props = sh.properties || {};
          const name = props.stakeholder_name || props.name || sh.title;
          const role = sh.node_subtype || props.role || 'unknown';
          const roleLower = role.toLowerCase().replace(/\s+/g, '_');
          const roleStyle = ROLE_STYLES[roleLower] || { bg: 'bg-gray-100', text: 'text-gray-800', label: role };
          const jobTitle = props.title || props.job_title || '';
          const influenceScore = props.influence_score != null ? Number(props.influence_score) : null;
          const engagement = props.engagement_frequency || props.engagement || '';
          const engLower = engagement.toLowerCase();
          const engStyle = ENGAGEMENT_STYLES[engLower] || { bg: 'bg-gray-50', text: 'text-gray-700' };

          return (
            <div
              key={sh.node_id}
              className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm hover:shadow-md transition-shadow"
            >
              {/* Header */}
              <div className="flex items-start gap-3 mb-3">
                <div className="flex-shrink-0 w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
                  <Users className="w-5 h-5 text-blue-600" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold text-gray-900 truncate">{name}</p>
                  {jobTitle && (
                    <div className="flex items-center gap-1 mt-0.5">
                      <Briefcase className="w-3 h-3 text-gray-400" />
                      <p className="text-xs text-gray-500 truncate">{jobTitle}</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Role badge */}
              <div className="flex flex-wrap gap-2 mb-3">
                <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${roleStyle.bg} ${roleStyle.text}`}>
                  {roleStyle.label}
                </span>
                {engagement && (
                  <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${engStyle.bg} ${engStyle.text}`}>
                    <Mail className="w-3 h-3" />
                    {engagement}
                  </span>
                )}
              </div>

              {/* Influence score */}
              {influenceScore != null && (
                <div className="mb-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-gray-500 flex items-center gap-1">
                      <TrendingUp className="w-3 h-3" />
                      Influence
                    </span>
                    <span className="text-xs font-medium text-gray-700">{Math.round(influenceScore)}</span>
                  </div>
                  <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{
                        width: `${Math.min(influenceScore, 100)}%`,
                        backgroundColor: influenceScore >= 70 ? '#16a34a' : influenceScore >= 40 ? '#d97706' : '#dc2626',
                      }}
                    />
                  </div>
                </div>
              )}

              {/* Revenue impact */}
              {sh.revenue_impact != null && sh.revenue_impact !== 0 && (
                <div className="pt-2 border-t border-gray-100">
                  <span className={`text-xs font-semibold ${
                    sh.revenue_impact_type === 'at_risk' ? 'text-red-600' :
                    sh.revenue_impact_type === 'expansion' ? 'text-blue-600' :
                    sh.revenue_impact_type === 'protected' ? 'text-green-600' :
                    'text-gray-600'
                  }`}>
                    Revenue: {fmtDollar(sh.revenue_impact)}
                  </span>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default StakeholderMap;
