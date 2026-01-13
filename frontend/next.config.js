/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  trailingSlash: true,
  output: 'export',
  images: {
    unoptimized: true
  },
  // Skip dynamic routes during static export
  experimental: {
    appDir: true
  }
}

module.exports = nextConfig
