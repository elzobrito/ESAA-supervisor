import React from 'react';
import { Play, RefreshCw, XCircle } from 'lucide-react';

interface Props {
  onRunNext: () => void;
  onRefresh: () => void;
  onCancel?: () => void;
  isRunning: boolean;
}

const RunControls: React.FC<Props> = ({ onRunNext, onRefresh, onCancel, isRunning }) => {
  return (
    <div className="run-controls">
      <button 
        className="btn-primary" 
        onClick={onRunNext} 
        disabled={isRunning}
      >
        {isRunning ? <RefreshCw size={16} className="spin" /> : <Play size={16} />}
        <span>Rodar Próxima Tarefa</span>
      </button>
      
      <button className="btn-secondary" onClick={onRefresh} disabled={isRunning}>
        <RefreshCw size={16} />
        <span>Atualizar Estado</span>
      </button>

      {isRunning && onCancel && (
        <button className="btn-danger" onClick={onCancel}>
          <XCircle size={16} />
          <span>Cancelar</span>
        </button>
      )}
    </div>
  );
};

export default RunControls;
