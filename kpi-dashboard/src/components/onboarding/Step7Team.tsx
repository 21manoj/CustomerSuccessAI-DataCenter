/**
 * Step 7: Team Setup
 */

import React, { useState } from 'react';
import { Users, Mail, X, CheckCircle, Send, UserPlus } from 'lucide-react';
import { TeamMember } from './OnboardingWizard.types';
import { TEAM_ROLES } from './OnboardingWizard.config';
import { isValidEmail } from './OnboardingWizard.utils';

interface Step7TeamProps {
  data: TeamMember[];
  onChange: (data: TeamMember[]) => void;
}

export const Step7Team: React.FC<Step7TeamProps> = ({ data, onChange }) => {
  const [newMember, setNewMember] = useState({ email: '', name: '', role: 'viewer' as const });
  const [emailError, setEmailError] = useState('');

  const handleAddMember = () => {
    if (!newMember.email || !newMember.name) {
      setEmailError('Email and name are required');
      return;
    }

    if (!isValidEmail(newMember.email)) {
      setEmailError('Please enter a valid email address');
      return;
    }

    if (data.some(m => m.email === newMember.email)) {
      setEmailError('This email is already in the list');
      return;
    }

    const member: TeamMember = {
      ...newMember,
      invited: false
    };

    onChange([...data, member]);
    setNewMember({ email: '', name: '', role: 'viewer' });
    setEmailError('');
  };

  const handleInvite = async (index: number) => {
    const member = data[index];
    // Simulate invitation
    const newData = [...data];
    newData[index] = {
      ...member,
      invited: true,
      invited_at: new Date().toISOString()
    };
    onChange(newData);

    // In real implementation, this would call an API
    setTimeout(() => {
      console.log(`Invitation sent to ${member.email}`);
    }, 500);
  };

  const handleRemove = (index: number) => {
    const newData = data.filter((_, i) => i !== index);
    onChange(newData);
  };

  return (
    <div className="space-y-6">
      <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <div className="flex items-start gap-2">
          <Users className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
          <div className="text-sm text-blue-800">
            <p className="font-medium mb-1">Invite Your Team</p>
            <p>Add team members who will use CustomerSuccessAI. You can invite more later.</p>
          </div>
        </div>
      </div>

      {/* Add New Member Form */}
      <div className="border rounded-lg p-4 bg-gray-50">
        <h4 className="font-medium mb-4 flex items-center gap-2">
          <UserPlus className="w-5 h-5" />
          Add Team Member
        </h4>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Name *</label>
            <input
              type="text"
              value={newMember.name}
              onChange={(e) => setNewMember({ ...newMember, name: e.target.value })}
              className="w-full px-3 py-2 border rounded-lg text-sm"
              placeholder="John Doe"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Email *</label>
            <input
              type="email"
              value={newMember.email}
              onChange={(e) => {
                setNewMember({ ...newMember, email: e.target.value });
                setEmailError('');
              }}
              className={`w-full px-3 py-2 border rounded-lg text-sm ${
                emailError ? 'border-red-500' : ''
              }`}
              placeholder="john@company.com"
            />
            {emailError && (
              <p className="text-xs text-red-600 mt-1">{emailError}</p>
            )}
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Role *</label>
            <select
              value={newMember.role}
              onChange={(e) => setNewMember({ ...newMember, role: e.target.value as any })}
              className="w-full px-3 py-2 border rounded-lg text-sm"
            >
              {TEAM_ROLES.map((role) => (
                <option key={role.id} value={role.id}>
                  {role.label}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="mt-4 flex items-center justify-between">
          <p className="text-xs text-gray-500">
            {TEAM_ROLES.find(r => r.id === newMember.role)?.description}
          </p>
          <button
            onClick={handleAddMember}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 flex items-center gap-2"
          >
            <UserPlus className="w-4 h-4" />
            Add Member
          </button>
        </div>
      </div>

      {/* Team Members List */}
      <div>
        <h4 className="font-medium mb-4">Team Members ({data.length})</h4>
        {data.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <Users className="w-12 h-12 mx-auto mb-2 text-gray-300" />
            <p>No team members added yet</p>
            <p className="text-sm">Add team members above to get started</p>
          </div>
        ) : (
          <div className="space-y-2">
            {data.map((member, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50"
              >
                <div className="flex items-center gap-4 flex-1">
                  <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
                    <Mail className="w-5 h-5 text-blue-600" />
                  </div>
                  <div className="flex-1">
                    <p className="font-medium">{member.name}</p>
                    <p className="text-sm text-gray-500">{member.email}</p>
                    <p className="text-xs text-gray-400 mt-1">
                      Role: {TEAM_ROLES.find(r => r.id === member.role)?.label}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {member.invited ? (
                    <div className="flex items-center gap-2 text-green-600">
                      <CheckCircle className="w-5 h-5" />
                      <span className="text-sm">Invited</span>
                    </div>
                  ) : (
                    <button
                      onClick={() => handleInvite(index)}
                      className="px-4 py-2 text-sm bg-blue-100 text-blue-700 rounded hover:bg-blue-200 flex items-center gap-2"
                    >
                      <Send className="w-4 h-4" />
                      Send Invitation
                    </button>
                  )}
                  <button
                    onClick={() => handleRemove(index)}
                    className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Role Descriptions */}
      <div className="p-4 bg-gray-50 rounded-lg">
        <h5 className="font-medium text-sm mb-3">Role Permissions:</h5>
        <div className="grid grid-cols-2 gap-3 text-xs">
          {TEAM_ROLES.map((role) => (
            <div key={role.id} className="flex items-start gap-2">
              <CheckCircle className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
              <div>
                <p className="font-medium">{role.label}:</p>
                <p className="text-gray-600">{role.description}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
