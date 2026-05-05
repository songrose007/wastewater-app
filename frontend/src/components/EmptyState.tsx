import { Link } from 'react-router-dom'

interface EmptyStateProps {
  message: string
  actionLabel?: string
  actionTo?: string
}

export default function EmptyState({ message, actionLabel, actionTo }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-20 gap-4">
      <svg className="w-16 h-16 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
      </svg>
      <p className="text-gray-500">{message}</p>
      {actionLabel && actionTo && (
        <Link
          to={actionTo}
          className="px-4 py-2 bg-primary text-white text-sm rounded-lg hover:bg-primary-light transition-colors"
        >
          {actionLabel}
        </Link>
      )}
    </div>
  )
}
