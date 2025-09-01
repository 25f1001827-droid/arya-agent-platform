
import React, { useState } from 'react'
import { Plus, Zap, Calendar, BarChart3 } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { toast } from 'react-hot-toast'

import { useContentStore } from '@/state/content'
import { usePagesStore } from '@/state/pages'
import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import Modal from '@/components/ui/Modal'
import Input from '@/components/ui/Input'

const QuickActions: React.FC = () => {
  const router = useRouter()
  const { generateContent, isGenerating } = useContentStore()
  const { pages } = usePagesStore()

  const [showQuickGenerate, setShowQuickGenerate] = useState(false)
  const [quickPrompt, setQuickPrompt] = useState('')
  const [selectedPageId, setSelectedPageId] = useState<number | null>(null)

  const handleQuickGenerate = async () => {
    if (!quickPrompt.trim() || !selectedPageId) {
      toast.error('Please enter a topic and select a page')
      return
    }

    const success = await generateContent({
      facebook_page_id: selectedPageId,
      ai_prompt: quickPrompt,
      content_type: 'MIXED',
      tone: 'engaging',
      include_hashtags: true,
      include_image: true
    })

    if (success) {
      toast.success('Content generated successfully!')
      setShowQuickGenerate(false)
      setQuickPrompt('')
      router.push('/content')
    }
  }

  const actions = [
    {
      title: 'Generate Content',
      description: 'Create AI-powered posts',
      icon: Zap,
      color: 'bg-green-500',
      onClick: () => setShowQuickGenerate(true)
    },
    {
      title: 'Add Facebook Page',
      description: 'Connect a new page',
      icon: Plus,
      color: 'bg-blue-500',
      onClick: () => router.push('/pages/add')
    },
    {
      title: 'Schedule Posts',
      description: 'Plan your content calendar',
      icon: Calendar,
      color: 'bg-purple-500',
      onClick: () => router.push('/scheduler')
    },
    {
      title: 'View Analytics',
      description: 'Check performance metrics',
      icon: BarChart3,
      color: 'bg-orange-500',
      onClick: () => router.push('/analytics')
    }
  ]

  return (
    <>
      <Card title="Quick Actions" subtitle="Get started with common tasks">
        <div className="grid grid-cols-2 gap-4">
          {actions.map((action, index) => (
            <button
              key={index}
              onClick={action.onClick}
              className="p-4 border border-gray-200 rounded-lg hover:border-gray-300 hover:shadow-sm transition-all text-left group"
            >
              <div className="flex items-center mb-3">
                <div className={`p-2 rounded-lg ${action.color}`}>
                  <action.icon className="h-5 w-5 text-white" />
                </div>
              </div>
              <h3 className="font-medium text-gray-900 group-hover:text-primary-600 mb-1">
                {action.title}
              </h3>
              <p className="text-sm text-gray-600">
                {action.description}
              </p>
            </button>
          ))}
        </div>
      </Card>

      {/* Quick Generate Modal */}
      <Modal
        isOpen={showQuickGenerate}
        onClose={() => setShowQuickGenerate(false)}
        title="Quick Content Generation"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select Facebook Page
            </label>
            <select
              value={selectedPageId || ''}
              onChange={(e) => setSelectedPageId(Number(e.target.value) || null)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="">Choose a page...</option>
              {pages.map((page) => (
                <option key={page.id} value={page.id}>
                  {page.page_name} ({page.region})
                </option>
              ))}
            </select>
          </div>

          <Input
            label="Content Topic"
            placeholder="e.g., 'Summer sale announcement' or 'Tech tips for productivity'"
            value={quickPrompt}
            onChange={(e) => setQuickPrompt(e.target.value)}
          />

          <div className="flex justify-end space-x-3 pt-4">
            <Button
              variant="outline"
              onClick={() => setShowQuickGenerate(false)}
            >
              Cancel
            </Button>
            <Button
              onClick={handleQuickGenerate}
              isLoading={isGenerating}
              disabled={isGenerating || !quickPrompt.trim() || !selectedPageId}
            >
              Generate Content
            </Button>
          </div>
        </div>
      </Modal>
    </>
  )
}

export default QuickActions
