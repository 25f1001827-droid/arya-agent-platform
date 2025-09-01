
import React from 'react'
import { cn } from '@/utils'
import type { CardProps } from '@/types'

const Card: React.FC<CardProps> = ({ 
  children, 
  title, 
  subtitle, 
  className 
}) => {
  return (
    <div className={cn(
      'bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden',
      className
    )}>
      {(title || subtitle) && (
        <div className="px-6 py-4 border-b border-gray-200">
          {title && (
            <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
          )}
          {subtitle && (
            <p className="mt-1 text-sm text-gray-600">{subtitle}</p>
          )}
        </div>
      )}
      <div className="p-6">
        {children}
      </div>
    </div>
  )
}

export default Card
