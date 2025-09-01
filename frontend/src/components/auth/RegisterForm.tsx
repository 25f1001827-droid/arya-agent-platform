
import React from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Mail, Lock, User, Eye, EyeOff, Globe } from 'lucide-react'
import { toast } from 'react-hot-toast'

import { useAuthStore } from '@/state/auth'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import type { RegisterForm as RegisterFormType } from '@/types'

// Validation schema
const registerSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
  username: z.string()
    .min(3, 'Username must be at least 3 characters')
    .max(50, 'Username must be less than 50 characters')
    .regex(/^[a-zA-Z0-9_]+$/, 'Username can only contain letters, numbers, and underscores'),
  password: z.string()
    .min(8, 'Password must be at least 8 characters')
    .regex(/[A-Z]/, 'Password must contain at least one uppercase letter')
    .regex(/[a-z]/, 'Password must contain at least one lowercase letter')
    .regex(/[0-9]/, 'Password must contain at least one number'),
  confirmPassword: z.string(),
  full_name: z.string().optional(),
  preferred_region: z.enum(['US', 'UK']).optional(),
  terms: z.boolean().refine(val => val === true, 'You must accept the terms and conditions')
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ["confirmPassword"]
})

type RegisterFormData = z.infer<typeof registerSchema>

const RegisterForm: React.FC = () => {
  const router = useRouter()
  const { register: registerUser, isLoading, error, clearError } = useAuthStore()
  const [showPassword, setShowPassword] = React.useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = React.useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors }
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      preferred_region: 'US'
    }
  })

  const onSubmit = async (data: RegisterFormData) => {
    clearError()

    const { confirmPassword, terms, ...userData } = data

    const success = await registerUser(userData)

    if (success) {
      toast.success('Account created successfully!')
      router.push('/dashboard')
    } else {
      toast.error(error || 'Registration failed')
    }
  }

  return (
    <div className="w-full max-w-md mx-auto">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Create your account
        </h1>
        <p className="text-gray-600">
          Start automating your social media today
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        <div className="grid grid-cols-2 gap-4">
          <div className="relative">
            <Input
              {...register('full_name')}
              type="text"
              label="Full name"
              placeholder="John Doe"
              className="pl-10"
            />
            <User className="absolute left-3 top-9 h-4 w-4 text-gray-400" />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Region
            </label>
            <select
              {...register('preferred_region')}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              <option value="US">🇺🇸 United States</option>
              <option value="UK">🇬🇧 United Kingdom</option>
            </select>
          </div>
        </div>

        <div className="relative">
          <Input
            {...register('email')}
            type="email"
            label="Email address"
            placeholder="john@example.com"
            required
            error={errors.email?.message}
            className="pl-10"
          />
          <Mail className="absolute left-3 top-9 h-4 w-4 text-gray-400" />
        </div>

        <div className="relative">
          <Input
            {...register('username')}
            type="text"
            label="Username"
            placeholder="johndoe"
            required
            error={errors.username?.message}
            className="pl-10"
          />
          <User className="absolute left-3 top-9 h-4 w-4 text-gray-400" />
        </div>

        <div className="relative">
          <Input
            {...register('password')}
            type={showPassword ? 'text' : 'password'}
            label="Password"
            placeholder="Create a strong password"
            required
            error={errors.password?.message}
            className="pl-10 pr-10"
          />
          <Lock className="absolute left-3 top-9 h-4 w-4 text-gray-400" />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute right-3 top-9 h-4 w-4 text-gray-400 hover:text-gray-600"
          >
            {showPassword ? <EyeOff /> : <Eye />}
          </button>
        </div>

        <div className="relative">
          <Input
            {...register('confirmPassword')}
            type={showConfirmPassword ? 'text' : 'password'}
            label="Confirm password"
            placeholder="Confirm your password"
            required
            error={errors.confirmPassword?.message}
            className="pl-10 pr-10"
          />
          <Lock className="absolute left-3 top-9 h-4 w-4 text-gray-400" />
          <button
            type="button"
            onClick={() => setShowConfirmPassword(!showConfirmPassword)}
            className="absolute right-3 top-9 h-4 w-4 text-gray-400 hover:text-gray-600"
          >
            {showConfirmPassword ? <EyeOff /> : <Eye />}
          </button>
        </div>

        <div>
          <label className="flex items-start">
            <input
              {...register('terms')}
              type="checkbox"
              className="rounded border-gray-300 text-primary-600 focus:ring-primary-500 mt-1"
            />
            <span className="ml-2 text-sm text-gray-600">
              I agree to the{' '}
              <Link href="/terms" className="text-primary-600 hover:text-primary-500">
                Terms of Service
              </Link>
              {' '}and{' '}
              <Link href="/privacy" className="text-primary-600 hover:text-primary-500">
                Privacy Policy
              </Link>
            </span>
          </label>
          {errors.terms && (
            <p className="mt-1 text-sm text-red-600">{errors.terms.message}</p>
          )}
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        <Button
          type="submit"
          className="w-full"
          isLoading={isLoading}
          disabled={isLoading}
        >
          {isLoading ? 'Creating account...' : 'Create account'}
        </Button>

        <div className="text-center">
          <p className="text-sm text-gray-600">
            Already have an account?{' '}
            <Link
              href="/auth/login"
              className="text-primary-600 hover:text-primary-500 font-medium"
            >
              Sign in
            </Link>
          </p>
        </div>
      </form>

      {/* Password requirements */}
      <div className="mt-6 p-4 bg-gray-50 rounded-lg">
        <h4 className="text-sm font-medium text-gray-900 mb-2">Password requirements:</h4>
        <ul className="text-xs text-gray-600 space-y-1">
          <li>• At least 8 characters long</li>
          <li>• Contains uppercase and lowercase letters</li>
          <li>• Contains at least one number</li>
        </ul>
      </div>
    </div>
  )
}

export default RegisterForm
