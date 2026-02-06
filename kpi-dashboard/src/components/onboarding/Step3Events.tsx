/**
 * Step 3: Event Severity Calibration (Vertical-Specific)
 */

import React from 'react';
import { AlertTriangle } from 'lucide-react';
import { EventSeverity } from './OnboardingWizard.types';

interface Step3EventsProps {
  data: EventSeverity[];
  onChange: (data: EventSeverity[]) => void;
}

export const Step3Events: React.FC<Step3EventsProps> = ({ data, onChange }) => {
  const handleSeverityChange = (id: string, severity: number) => {
    const newData = data.map((event) =>
      event.id === id ? { ...event, severity } : event
    );
    onChange(newData);
  };

  const negativeEvents = data.filter((e) => e.type === 'negative');
  const positiveEvents = data.filter((e) => e.type === 'positive');

  return (
    <div className="space-y-6">
      <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <div className="flex items-start gap-2">
          <AlertTriangle className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
          <div className="text-sm text-blue-800">
            <p className="font-medium mb-1">Rate Event Severity</p>
            <p>Adjust the severity rating for each event based on how critical they are for your business. Scale: 1 = Minor, 10 = Critical.</p>
          </div>
        </div>
      </div>

      <div className="space-y-4">
        <h4 className="font-medium text-red-700">⚠️ Negative Events</h4>
        {negativeEvents.map((event) => (
          <div key={event.id} className="flex items-center gap-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex-1">
              <p className="font-medium text-sm">{event.name}</p>
              <p className="text-xs text-gray-500 mt-1">
                Higher severity = Greater impact on health score
              </p>
            </div>
            <div className="flex items-center gap-4">
              <input
                type="range"
                min={1}
                max={10}
                value={event.severity}
                onChange={(e) => handleSeverityChange(event.id, Number(e.target.value))}
                className="w-32"
              />
              <span className="w-10 text-center font-bold text-red-700">{event.severity}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="space-y-4 mt-6">
        <h4 className="font-medium text-green-700">✅ Positive Events</h4>
        {positiveEvents.map((event) => (
          <div key={event.id} className="flex items-center gap-4 p-4 bg-green-50 border border-green-200 rounded-lg">
            <div className="flex-1">
              <p className="font-medium text-sm">{event.name}</p>
              <p className="text-xs text-gray-500 mt-1">
                Higher severity = Greater positive impact on health score
              </p>
            </div>
            <div className="flex items-center gap-4">
              <input
                type="range"
                min={1}
                max={10}
                value={event.severity}
                onChange={(e) => handleSeverityChange(event.id, Number(e.target.value))}
                className="w-32"
              />
              <span className="w-10 text-center font-bold text-green-700">{event.severity}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-6 p-4 bg-gray-50 rounded-lg">
        <p className="text-sm text-gray-700">
          <strong>Tip:</strong> Events with severity ≥ 8 will trigger immediate alerts. 
          Adjust these based on your business priorities.
        </p>
      </div>
    </div>
  );
};
