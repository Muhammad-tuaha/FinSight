import { initializeApp, getApps, getApp } from 'firebase/app'
import {
  getAuth,
  GoogleAuthProvider,
  signInWithPopup,
  signOut as firebaseSignOut,
  onAuthStateChanged,
  User,
} from 'firebase/auth'

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY || 'AIzaSyDYwYjHbsnfYsHKq_xUB69ZBaKVaxT46oM',
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN || 'finsight-fa6ee.firebaseapp.com',
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID || 'finsight-fa6ee',
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET || 'finsight-fa6ee.appspot.com',
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID || '112236409750578942717',
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID || '1:112236409750578942717:web:finsight',
}

const app = !getApps().length ? initializeApp(firebaseConfig) : getApp()
export const auth = getAuth(app)
export const googleProvider = new GoogleAuthProvider()

export async function signInWithGoogle(): Promise<User> {
  const result = await signInWithPopup(auth, googleProvider)
  return result.user
}

export async function getAuthToken(): Promise<string | null> {
  const currentUser = auth.currentUser
  if (!currentUser) return null
  return currentUser.getIdToken()
}

export async function signOutUser(): Promise<void> {
  return firebaseSignOut(auth)
}

