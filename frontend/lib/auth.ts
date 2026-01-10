/**
 * Authentication utilities for Stock Analysis frontend
 * Handles Cognito authentication and token management using AWS SDK v3
 */

import {
  CognitoIdentityProviderClient,
  InitiateAuthCommand,
  SignUpCommand,
  ConfirmSignUpCommand,
  ResendConfirmationCodeCommand,
  ForgotPasswordCommand,
  ConfirmForgotPasswordCommand,
  GetUserCommand,
  AuthFlowType,
  ChallengeNameType
} from '@aws-sdk/client-cognito-identity-provider'

// Cognito configuration - these will be set from environment variables
const COGNITO_CONFIG = {
  userPoolId: process.env.NEXT_PUBLIC_USER_POOL_ID || '',
  clientId: process.env.NEXT_PUBLIC_USER_POOL_CLIENT_ID || '',
  identityPoolId: process.env.NEXT_PUBLIC_IDENTITY_POOL_ID || '',
  region: process.env.NEXT_PUBLIC_AWS_REGION || 'eu-west-1'
}

// Initialize Cognito client
const cognitoClient = new CognitoIdentityProviderClient({
  region: COGNITO_CONFIG.region
})

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

interface TokenData {
  accessToken: string
  idToken: string
  refreshToken: string
  expiresAt: number
}

class AuthService {
  private tokenData: TokenData | null = null
  private authStateListeners: ((state: AuthState) => void)[] = []

  constructor() {
    // Check for existing session on initialization
    this.loadStoredTokens()
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
   * Load stored tokens from localStorage
   */
  private loadStoredTokens() {
    try {
      const stored = localStorage.getItem('auth_tokens')
      if (stored) {
        const tokenData = JSON.parse(stored) as TokenData
        
        // Check if tokens are still valid
        if (tokenData.expiresAt > Date.now()) {
          this.tokenData = tokenData
          this.notifyAuthStateChange()
        } else {
          // Tokens expired, clear them
          localStorage.removeItem('auth_tokens')
        }
      }
    } catch (error) {
      console.error('Error loading stored tokens:', error)
      localStorage.removeItem('auth_tokens')
    }
  }

  /**
   * Store tokens in localStorage
   */
  private storeTokens(tokenData: TokenData) {
    try {
      localStorage.setItem('auth_tokens', JSON.stringify(tokenData))
      this.tokenData = tokenData
    } catch (error) {
      console.error('Error storing tokens:', error)
    }
  }

  /**
   * Parse JWT token payload
   */
  private parseJwtPayload(token: string): any {
    try {
      const base64Url = token.split('.')[1]
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
      const jsonPayload = decodeURIComponent(
        atob(base64)
          .split('')
          .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
          .join('')
      )
      return JSON.parse(jsonPayload)
    } catch (error) {
      console.error('Error parsing JWT:', error)
      return null
    }
  }

  /**
   * Get current authentication state
   */
  getAuthState(): AuthState {
    if (!this.tokenData || this.tokenData.expiresAt <= Date.now()) {
      return {
        isAuthenticated: false,
        user: null,
        token: null,
        loading: false
      }
    }

    const payload = this.parseJwtPayload(this.tokenData.idToken)
    if (!payload) {
      return {
        isAuthenticated: false,
        user: null,
        token: null,
        loading: false
      }
    }

    return {
      isAuthenticated: true,
      user: {
        userId: payload.sub,
        username: payload['cognito:username'] || payload.email,
        email: payload.email,
        emailVerified: payload.email_verified || false,
        givenName: payload.given_name,
        familyName: payload.family_name,
        subscriptionTier: payload['custom:subscription_tier'] || 'free'
      },
      token: this.tokenData.idToken,
      loading: false
    }
  }

  /**
   * Sign in with username and password
   */
  async signIn(username: string, password: string): Promise<UserInfo> {
    try {
      const command = new InitiateAuthCommand({
        AuthFlow: AuthFlowType.USER_PASSWORD_AUTH,
        ClientId: COGNITO_CONFIG.clientId,
        AuthParameters: {
          USERNAME: username,
          PASSWORD: password
        }
      })

      const response = await cognitoClient.send(command)

      if (response.AuthenticationResult) {
        const { AccessToken, IdToken, RefreshToken, ExpiresIn } = response.AuthenticationResult

        if (AccessToken && IdToken && RefreshToken) {
          const tokenData: TokenData = {
            accessToken: AccessToken,
            idToken: IdToken,
            refreshToken: RefreshToken,
            expiresAt: Date.now() + (ExpiresIn! * 1000)
          }

          this.storeTokens(tokenData)
          this.notifyAuthStateChange()

          const userInfo = this.getAuthState().user!
          return userInfo
        }
      }

      throw new Error('Authentication failed')
    } catch (error: any) {
      console.error('Sign in error:', error)
      throw new Error(error.message || 'Sign in failed')
    }
  }

  /**
   * Sign up new user
   */
  async signUp(username: string, email: string, password: string, givenName?: string, familyName?: string): Promise<void> {
    try {
      const userAttributes = [
        {
          Name: 'email',
          Value: email
        }
      ]

      if (givenName) {
        userAttributes.push({
          Name: 'given_name',
          Value: givenName
        })
      }

      if (familyName) {
        userAttributes.push({
          Name: 'family_name',
          Value: familyName
        })
      }

      // Add default subscription tier
      userAttributes.push({
        Name: 'custom:subscription_tier',
        Value: 'free'
      })

      const command = new SignUpCommand({
        ClientId: COGNITO_CONFIG.clientId,
        Username: username,
        Password: password,
        UserAttributes: userAttributes
      })

      await cognitoClient.send(command)
    } catch (error: any) {
      console.error('Sign up error:', error)
      throw new Error(error.message || 'Sign up failed')
    }
  }

  /**
   * Confirm sign up with verification code
   */
  async confirmSignUp(username: string, code: string): Promise<void> {
    try {
      const command = new ConfirmSignUpCommand({
        ClientId: COGNITO_CONFIG.clientId,
        Username: username,
        ConfirmationCode: code
      })

      await cognitoClient.send(command)
    } catch (error: any) {
      console.error('Confirmation error:', error)
      throw new Error(error.message || 'Confirmation failed')
    }
  }

  /**
   * Resend confirmation code
   */
  async resendConfirmationCode(username: string): Promise<void> {
    try {
      const command = new ResendConfirmationCodeCommand({
        ClientId: COGNITO_CONFIG.clientId,
        Username: username
      })

      await cognitoClient.send(command)
    } catch (error: any) {
      console.error('Resend confirmation error:', error)
      throw new Error(error.message || 'Resend confirmation failed')
    }
  }

  /**
   * Initiate forgot password flow
   */
  async forgotPassword(username: string): Promise<void> {
    try {
      const command = new ForgotPasswordCommand({
        ClientId: COGNITO_CONFIG.clientId,
        Username: username
      })

      await cognitoClient.send(command)
    } catch (error: any) {
      console.error('Forgot password error:', error)
      throw new Error(error.message || 'Forgot password failed')
    }
  }

  /**
   * Confirm forgot password with new password
   */
  async confirmPassword(username: string, code: string, newPassword: string): Promise<void> {
    try {
      const command = new ConfirmForgotPasswordCommand({
        ClientId: COGNITO_CONFIG.clientId,
        Username: username,
        ConfirmationCode: code,
        Password: newPassword
      })

      await cognitoClient.send(command)
    } catch (error: any) {
      console.error('Confirm password error:', error)
      throw new Error(error.message || 'Confirm password failed')
    }
  }

  /**
   * Sign out current user
   */
  signOut(): void {
    this.tokenData = null
    localStorage.removeItem('auth_tokens')
    this.notifyAuthStateChange()
  }

  /**
   * Get current access token for API calls
   */
  getAccessToken(): string | null {
    if (this.tokenData && this.tokenData.expiresAt > Date.now()) {
      return this.tokenData.idToken
    }
    return null
  }

  /**
   * Check if user is authenticated
   */
  isAuthenticated(): boolean {
    return !!(this.tokenData && this.tokenData.expiresAt > Date.now())
  }

  /**
   * Get user info
   */
  getCurrentUser(): UserInfo | null {
    return this.getAuthState().user
  }
}

// Export singleton instance
export const authService = new AuthService()

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