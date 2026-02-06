/**
 * Step 8: Training & Walkthrough (Optional)
 */

import React from 'react';
import { BookOpen, Play, ExternalLink, CheckCircle, X, Rocket } from 'lucide-react';

interface Step8TrainingProps {
  skipTraining: boolean;
  onSkipChange: (skip: boolean) => void;
}

export const Step8Training: React.FC<Step8TrainingProps> = ({ skipTraining, onSkipChange }) => {
  const resources = [
    {
      title: 'Product Tour',
      description: 'Interactive walkthrough of key features',
      type: 'tour',
      duration: '5 min'
    },
    {
      title: 'Getting Started Video',
      description: 'Learn the basics of CustomerSuccessAI',
      type: 'video',
      duration: '10 min',
      url: '#'
    },
    {
      title: 'Documentation',
      description: 'Complete guide and API reference',
      type: 'docs',
      url: '#'
    },
    {
      title: 'Best Practices Guide',
      description: 'Tips for effective customer success management',
      type: 'guide',
      duration: '15 min'
    }
  ];

  return (
    <div className="space-y-6">
      <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
        <div className="flex items-start gap-2">
          <CheckCircle className="w-5 h-5 text-green-600 mt-0.5 flex-shrink-0" />
          <div className="text-sm text-green-800">
            <p className="font-medium mb-1">Setup Complete! 🎉</p>
            <p>Your account is ready. Would you like to take a quick tour to learn the platform?</p>
          </div>
        </div>
      </div>

      {!skipTraining && (
        <div className="space-y-4">
          <div>
            <h4 className="font-medium mb-4 flex items-center gap-2">
              <BookOpen className="w-5 h-5" />
              Recommended Resources
            </h4>
            <div className="grid grid-cols-2 gap-4">
              {resources.map((resource, index) => (
                <div
                  key={index}
                  className="p-4 border-2 border-gray-200 rounded-lg hover:border-blue-300 hover:bg-blue-50 transition-all cursor-pointer"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <h5 className="font-medium">{resource.title}</h5>
                      <p className="text-sm text-gray-600 mt-1">{resource.description}</p>
                    </div>
                    {resource.type === 'video' && <Play className="w-5 h-5 text-blue-600" />}
                    {resource.type === 'docs' && <ExternalLink className="w-5 h-5 text-blue-600" />}
                    {resource.type === 'tour' && <Rocket className="w-5 h-5 text-blue-600" />}
                  </div>
                  {resource.duration && (
                    <p className="text-xs text-gray-500 mt-2">⏱️ {resource.duration}</p>
                  )}
                  {resource.url && (
                    <a
                      href={resource.url}
                      className="text-xs text-blue-600 hover:underline mt-2 inline-block"
                    >
                      View →
                    </a>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <h5 className="font-medium text-sm mb-2">Quick Start Options:</h5>
            <div className="space-y-2">
              <button className="w-full px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center justify-center gap-2">
                <Rocket className="w-5 h-5" />
                Start Interactive Tour (Recommended)
              </button>
              <button className="w-full px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50">
                Watch Getting Started Video
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="border-t pt-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="font-medium">Skip Training</p>
            <p className="text-sm text-gray-500">
              You can access tutorials anytime from the help menu
            </p>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={skipTraining}
              onChange={(e) => onSkipChange(e.target.checked)}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
          </label>
        </div>
      </div>

      {skipTraining && (
        <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
          <p className="text-sm text-yellow-800">
            <strong>Note:</strong> You're skipping the training. You can access tutorials anytime from the help menu (?) in the top navigation.
          </p>
        </div>
      )}
    </div>
  );
};
