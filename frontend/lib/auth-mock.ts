/**
 * Mock authentication system for development and testing
 * This allows us to test the UI without deploying Cognito infrastructure
 */

export interface UserInfo {
  userId: string
  username: string
  email: string
  emailVerified: boolean
  givenName?: string
  familyName?: string
  subscriptionTier: string
}

export interface AuthState {
  isAuthenticated: boolean
  user: UserInfo | null
  token: string | null
  loading: boolean
}

// Mock users database
const MOCK_USERS = [
  {
    username: 'ryandscholtz',
    email: 'ryandscholtz@gmail.com',
    password: 'TestPass123',
    userId: 'mock-user-1',
    givenName: 'Ryan',
    familyName: 'Scholtz',
    subscriptionTier: 'premium',
    emailVerified: true
  },
  {
    username: 'testuser',
    email: 'test@example.com',
    password: 'TestPass123',
    userId: 'mock-user-2',
    givenName: 'Test',
    familyName: 'User',
    subscriptionTier: 'free',
    emailVerified: true
  }
]

class MockAuthService {
  private currentUser: UserInfo | null = null
  private authStateListeners: ((state: AuthState) => void)[] = []

  constructor() {
    // Only initialize on client side
    if (typeof window !== 'undefined') {
      // Check for existing session on initialization
      this.loadStoredUser()
    }
  }

  /**
   * Add listener for auth state changes
   */
  onAuthStateChange(callback: (state: AuthState) => void) {
    this.authStateListeners.push(callback)
    
    // Return unsubscribe function
    return () => {
      this.authStateListeners = this.authStateListeners.filter(listener => listener !== callback)
    }
  }

  /**
   * Notify all listeners of auth state change
   */
  private notifyAuthStateChange() {
    const state = this.getAuthState()
    this.authStateListeners.forEach(listener => listener(state))
  }

  /**
   * Load stored user from localStorage
   */
  private loadStoredUser() {
    // Only run on client side
    if (typeof window === 'undefined') return
    
    try {
      const stored = localStorage.getItem('mock_auth_user')
      if (stored) {
        this.currentUser = JSON.parse(stored)
        this.notifyAuthStateChange()
      }
    } catch (error) {
      console.error('Error loading stored user:', error)
      localStorage.removeItem('mock_auth_user')
    }
  }

  /**
   * Store user in localStorage
   */
  private storeUser(user: UserInfo) {
    // Only run on client side
    if (typeof window === 'undefined') return
    
    try {
      localStorage.setItem('mock_auth_user', JSON.stringify(user))
      this.currentUser = user
    } catch (error) {
      console.error('Error storing user:', error)
    }
  }

  /**
   * Get current authentication state
   */
  getAuthState(): AuthState {
    return {
      isAuthenticated: !!this.currentUser,
      user: this.currentUser,
      token: this.currentUser ? 'mock-jwt-token' : null,
      loading: false
    }
  }

  /**
   * Sign in with username and password
   */
  async signIn(username: string, password: string): Promise<UserInfo> {
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 1000))

    const user = MOCK_USERS.find(u => 
      (u.username === username || u.email === username) && u.password === password
    )

    if (!user) {
      throw new Error('Invalid username or password')
    }

    const userInfo: UserInfo = {
      userId: user.userId,
      username: user.username,
      email: user.email,
      emailVerified: user.emailVerified,
      givenName: user.givenName,
      familyName: user.familyName,
      subscriptionTier: user.subscriptionTier
    }

    this.storeUser(userInfo)
    this.notifyAuthStateChange()

    return userInfo
  }

  /**
   * Sign up new user
   */
  async signUp(username: string, email: string, password: string, givenName?: string, familyName?: string): Promise<void> {
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 1500))

    // Check if user already exists
    const existingUser = MOCK_USERS.find(u => u.username === username || u.email === email)
    if (existingUser) {
      throw new Error('User already exists')
    }

    // In a real implementation, this would create the user in Cognito
    console.log('Mock sign up successful for:', { username, email, givenName, familyName })
  }

  /**
   * Confirm sign up with verification code
   */
  async confirmSignUp(username: string, code: string): Promise<void> {
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 1000))

    if (code !== '123456') {
      throw new Error('Invalid verification code')
    }

    console.log('Mock confirmation successful for:', username)
  }

  /**
   * Resend confirmation code
   */
  async resendConfirmationCode(username: string): Promise<void> {
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 1000))
    console.log('Mock confirmation code resent to:', username)
  }

  /**
   * Initiate forgot password flow
   */
  async forgotPassword(username: string): Promise<void> {
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 1000))
    console.log('Mock forgot password initiated for:', username)
  }

  /**
   * Confirm forgot password with new password
   */
  async confirmPassword(username: string, code: string, newPassword: string): Promise<void> {
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 1000))

    if (code !== '123456') {
      throw new Error('Invalid verification code')
    }

    console.log('Mock password reset successful for:', username)
  }

  /**
   * Sign out current user
   */
  signOut(): void {
    this.currentUser = null
    
    // Only run on client side
    if (typeof window !== 'undefined') {
      localStorage.removeItem('mock_auth_user')
    }
    
    this.notifyAuthStateChange()
  }

  /**
   * Get current access token for API calls
   */
  getAccessToken(): string | null {
    return this.currentUser ? 'mock-jwt-token' : null
  }

  /**
   * Check if user is authenticated
   */
  isAuthenticated(): boolean {
    return !!this.currentUser
  }

  /**
   * Get user info
   */
  getCurrentUser(): UserInfo | null {
    return this.currentUser
  }
}

// Export singleton instance
export const authService = new MockAuthService()

// Export utility functions
export const useAuth = () => {
  return authService.getAuthState()
}

export const requireAuth = () => {
  const authState = authService.getAuthState()
  if (!authState.isAuthenticated) {
    throw new Error('Authentication required')
  }
  return authState
}