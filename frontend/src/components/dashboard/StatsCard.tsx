
import React from 'react'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { cn, formatNumber, formatPercentage } from '@/utils'

interface StatsCardProps {
  title: string
  value: number | string
  change?: number
  changeLabel?: string
  icon?: React.ComponentType<{ className?: string }>
  format?: 'number' | 'currency' | 'percentage'
  className?: string
}

const StatsCard: React.FC<StatsCardProps> = ({
  title,
  value,
  change,
  changeLabel,
  icon: Icon,
  format = 'number',
  className
}) => {
  const formatValue = (val: number | string) => {
    if (typeof val === 'string') return val

    switch (format) {
      case 'currency':
        return `$${formatNumber(val)}`
      case 'percentage':
        return formatPercentage(val)
      default:
        return formatNumber(val)
    }
  }

  const getTrendIcon = () => {
    if (change === undefined) return null
    if (change > 0) return <TrendingUp className="h-4 w-4 text-green-600" />
    if (change < 0) return <TrendingDown className="h-4 w-4 text-red-600" />
    return <Minus className="h-4 w-4 text-gray-400" />
  }

  const getTrendColor = () => {
    if (change === undefined) return 'text-gray-600'
    if (change > 0) return 'text-green-600'
    if (change < 0) return 'text-red-600'
    return 'text-gray-600'
  }

  return (
    <div className={cn(
      'bg-white rounded-lg border border-gray-200 p-6',
      className
    )}>
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-600 mb-2">{title}</p>
          <p className="text-3xl font-bold text-gray-900">
            {formatValue(value)}
          </p>
          {change !== undefined && (
            <div className="flex items-center mt-2">
              {getTrendIcon()}
              <span className={cn('text-sm font-medium ml-1', getTrendColor())}>
                {change > 0 && '+'}
                {formatPercentage(Math.abs(change))}
              </span>
              {changeLabel && (
                <span className="text-sm text-gray-500 ml-1">{changeLabel}</span>
              )}
            </div>
          )}
        </div>
        {Icon && (
          <div className="ml-4">
            <div className="p-3 bg-primary-50 rounded-lg">
              <Icon className="h-6 w-6 text-primary-600" />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default StatsCard
