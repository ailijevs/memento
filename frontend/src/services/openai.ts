import OpenAI from 'openai'

// Initialize OpenAI client lazily to avoid crashes if API key isn't set
let openai: OpenAI | null = null

function getOpenAIClient(): OpenAI {
  if (!openai) {
    const apiKey = import.meta.env.VITE_OPENAI_API_KEY || 'dummy-key'
    openai = new OpenAI({
      apiKey,
      dangerouslyAllowBrowser: true, // Only for demo purposes!
    })
  }
  return openai
}

/**
 * Generate conversation starters based on profile data
 */
export async function generateConversationStarters(
  name: string,
  role: string,
  sharedInterests: string[]
): Promise<string[]> {
  try {
    // Check if API key is set
    const apiKey = import.meta.env.VITE_OPENAI_API_KEY
    console.log('API Key exists:', !!apiKey)
    console.log('API Key starts with:', apiKey?.substring(0, 10))
    
    if (!apiKey) {
      return [
        'Please set VITE_OPENAI_API_KEY in your .env file to use AI features',
        'Get your API key from: https://platform.openai.com/api-keys'
      ]
    }

    const prompt = `Generate 3 casual, friendly conversation starters for meeting someone named ${name} who is a ${role}. We share these interests: ${sharedInterests.join(', ')}. Keep them natural and not too formal.`

    console.log('Making OpenAI API call...')
    const client = getOpenAIClient()
    const response = await client.chat.completions.create({
      model: 'gpt-3.5-turbo',
      messages: [
        {
          role: 'system',
          content:
            'You are a helpful assistant that generates natural conversation starters for networking events.',
        },
        {
          role: 'user',
          content: prompt,
        },
      ],
      temperature: 0.8,
      max_tokens: 200,
    })

    console.log('OpenAI API response:', response)
    const content = response.choices[0]?.message?.content || ''
    
    // Parse the response into array (assuming GPT returns numbered list)
    const starters = content
      .split('\n')
      .filter((line) => line.trim().length > 0)
      .map((line) => line.replace(/^\d+\.\s*/, '').trim())
      .filter((line) => line.length > 0)

    return starters.length > 0 ? starters : [
      'Could not generate conversation starters. Try again!'
    ]
  } catch (error: any) {
    console.error('OpenAI API Error Details:', error)
    console.error('Error message:', error?.message)
    console.error('Error status:', error?.status)
    console.error('Error response:', error?.response?.data)
    
    // Return more specific error messages - or use fallback
    if (error?.status === 429) {
      // Rate limit hit - use smart fallback instead
      console.log('Rate limit hit, using fallback generator...')
      return generateFallbackStarters(name, role, sharedInterests)
    } else if (error?.status === 401) {
      return ['Invalid API key. Please check your OpenAI API key.']
    } else if (error?.status === 403) {
      return ['API key lacks permissions. Check if your key has access to GPT-3.5.']
    } else {
      return [`Error: ${error?.message || 'Unknown error occurred'}`]
    }
  }
}

/**
 * Fallback conversation starter generator (used when API rate limit hit)
 */
function generateFallbackStarters(
  name: string,
  role: string,
  sharedInterests: string[]
): string[] {
  const starters: string[] = []
  
  // Starter based on shared interests
  if (sharedInterests.length > 0) {
    const interest = sharedInterests[0]
    starters.push(`Hey ${name}! I noticed we both have a connection to ${interest} - how did you get involved with that?`)
  }
  
  // Starter based on their role
  const roleKeywords = role.toLowerCase()
  if (roleKeywords.includes('product') || roleKeywords.includes('pm')) {
    starters.push(`What's the most challenging product decision you've had to make recently?`)
  } else if (roleKeywords.includes('engineer') || roleKeywords.includes('developer')) {
    starters.push(`What's your favorite tech stack to work with these days?`)
  } else if (roleKeywords.includes('design')) {
    starters.push(`I'd love to hear about your design process - how do you approach new projects?`)
  } else if (roleKeywords.includes('founder') || roleKeywords.includes('ceo')) {
    starters.push(`What's been the biggest surprise in your entrepreneurial journey?`)
  } else if (roleKeywords.includes('vc') || roleKeywords.includes('investor')) {
    starters.push(`What trends are you most excited about in the startup space right now?`)
  } else {
    starters.push(`What's been keeping you busy lately at work?`)
  }
  
  // Starter based on second shared interest or generic
  if (sharedInterests.length > 1) {
    const interest2 = sharedInterests[1]
    starters.push(`I see you're also into ${interest2} - any recommendations for someone looking to learn more?`)
  } else {
    starters.push(`How did you end up in your current role? I'd love to hear the journey!`)
  }
  
  return starters
}

/**
 * Generate a professional summary for a profile
 */
export async function generateProfileSummary(
  name: string,
  role: string,
  interests: string[]
): Promise<string> {
  try {
    if (!import.meta.env.VITE_OPENAI_API_KEY) {
      return 'API key not configured'
    }

    const prompt = `Write a brief, engaging professional summary (2-3 sentences) for ${name}, a ${role} who is interested in: ${interests.join(', ')}.`

    const client = getOpenAIClient()
    const response = await client.chat.completions.create({
      model: 'gpt-3.5-turbo',
      messages: [
        {
          role: 'user',
          content: prompt,
        },
      ],
      temperature: 0.7,
      max_tokens: 100,
    })

    return response.choices[0]?.message?.content || 'No summary available.'
  } catch (error) {
    console.error('OpenAI API Error:', error)
    return 'Error generating summary.'
  }
}

