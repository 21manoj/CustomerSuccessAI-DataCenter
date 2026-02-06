/**
 * Step 2: Vertical-Specific KPI Pillar Configuration
 */

import React, { useState } from 'react';
import { GripVertical, Info } from 'lucide-react';
import { PillarRanking } from './OnboardingWizard.types';

interface Step2PillarsProps {
  data: PillarRanking[];
  onChange: (data: PillarRanking[]) => void;
}

export const Step2Pillars: React.FC<Step2PillarsProps> = ({ data, onChange }) => {
  const [dragging, setDragging] = useState<number | null>(null);

  const handleDragStart = (index: number) => {
    setDragging(index);
  };

  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault();
    if (dragging === null || dragging === index) return;

    const newData = [...data];
    const draggedItem = newData[dragging];
    newData.splice(dragging, 1);
    newData.splice(index, 0, draggedItem);
    
    // Update ranks
    newData.forEach((item, i) => {
      item.rank = i + 1;
    });

    onChange(newData);
    setDragging(index);
  };

  const handleDragEnd = () => {
    setDragging(null);
  };

  const calculateWeight = (rank: number, total: number): number => {
    if (rank === 1) return 30;
    if (rank <= 3) return 20;
    return 15;
  };

  return (
    <div className="space-y-4">
      <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <div className="flex items-start gap-2">
          <Info className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
          <div className="text-sm text-blue-800">
            <p className="font-medium mb-1">Rank Your Pillars by Importance</p>
            <p>Drag and drop to reorder. Your #1 pillar will have the highest weight (30%) in health score calculations.</p>
          </div>
        </div>
      </div>

      <p className="text-gray-600 mb-4">
        Drag to reorder by importance to YOUR business. #1 = Most Important
      </p>
      
      {data.sort((a, b) => a.rank - b.rank).map((pillar, index) => {
        const weight = calculateWeight(pillar.rank, data.length);
        return (
          <div
            key={pillar.id}
            draggable
            onDragStart={() => handleDragStart(index)}
            onDragOver={(e) => handleDragOver(e, index)}
            onDragEnd={handleDragEnd}
            className={`flex items-center gap-4 p-4 bg-white border-2 rounded-lg cursor-move transition-all ${
              dragging === index ? 'opacity-50 scale-95' : 'hover:shadow-md'
            } ${index === 0 ? 'border-blue-300' : 'border-gray-200'}`}
          >
            <div className="flex items-center gap-3">
              <GripVertical className="w-5 h-5 text-gray-400" />
              <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-white ${
                index === 0 ? 'bg-blue-600' :
                index === 1 ? 'bg-blue-500' :
                index === 2 ? 'bg-blue-400' :
                index === 3 ? 'bg-gray-400' :
                'bg-gray-300'
              }`}>
                {pillar.rank}
              </div>
            </div>
            <div className="flex-1">
              <h4 className="font-medium">{pillar.label}</h4>
              <p className="text-sm text-gray-500">{pillar.description}</p>
              {pillar.kpis && pillar.kpis.length > 0 && (
                <p className="text-xs text-gray-400 mt-1">
                  KPIs: {pillar.kpis.slice(0, 3).join(', ')}
                  {pillar.kpis.length > 3 && ` +${pillar.kpis.length - 3} more`}
                </p>
              )}
            </div>
            <div className="text-right">
              <div className="text-lg font-bold text-blue-600">{weight}%</div>
              <div className="text-xs text-gray-500">Weight</div>
            </div>
            <div className="text-sm text-gray-400 w-24 text-right">
              {index === 0 && '← Most Important'}
              {index === data.length - 1 && '← Least Important'}
            </div>
          </div>
        );
      })}

      <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded-lg">
        <p className="text-sm text-green-800">
          <strong>Weight Distribution:</strong>
        </p>
        <ul className="text-sm text-green-700 mt-2 space-y-1">
          <li>• #1 Pillar: 30% weight</li>
          <li>• #2-3 Pillars: 20% weight each</li>
          <li>• #4-5 Pillars: 15% weight each</li>
          <li>• Total: 100% (weights automatically balanced)</li>
        </ul>
      </div>
    </div>
  );
};
