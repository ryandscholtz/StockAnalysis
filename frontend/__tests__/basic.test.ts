/**
 * Basic frontend tests to verify Jest is working
 */

describe('Basic Frontend Tests', () => {
  it('should perform basic JavaScript operations', () => {
    expect(1 + 1).toBe(2)
    expect('hello'.toUpperCase()).toBe('HELLO')
    expect([1, 2, 3]).toHaveLength(3)
  })

  it('should handle arrays and objects', () => {
    const testArray = [1, 2, 3, 4, 5]
    expect(testArray.filter(n => n > 3)).toEqual([4, 5])
    
    const testObject = { name: 'test', value: 42 }
    expect(testObject.name).toBe('test')
    expect(testObject.value).toBe(42)
  })

  it('should handle promises', async () => {
    const promise = Promise.resolve('success')
    await expect(promise).resolves.toBe('success')
  })

  it('should handle string operations', () => {
    const text = 'Stock Analysis Tool'
    expect(text.toLowerCase()).toBe('stock analysis tool')
    expect(text.includes('Analysis')).toBe(true)
    expect(text.split(' ')).toHaveLength(3)
  })

  it('should handle date operations', () => {
    const date = new Date('2024-01-01')
    expect(date.getFullYear()).toBe(2024)
    expect(date.getMonth()).toBe(0) // January is 0
  })
})