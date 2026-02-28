/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  trailingSlash: true,
  output: 'export',
  distDir: 'out',
  images: {
    unoptimized: true
  },
  env: {
    NEXT_PUBLIC_API_URL: 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production'
  }
}

module.exports = nextConfig
