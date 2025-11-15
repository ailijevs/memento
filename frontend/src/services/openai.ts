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
    if (!import.meta.env.VITE_OPENAI_API_KEY) {
      return [
        'Please set VITE_OPENAI_API_KEY in your .env file to use AI features',
        'Get your API key from: https://platform.openai.com/api-keys'
      ]
    }

    const prompt = `Generate 3 casual, friendly conversation starters for meeting someone named ${name} who is a ${role}. We share these interests: ${sharedInterests.join(', ')}. Keep them natural and not too formal.`

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
  } catch (error) {
    console.error('OpenAI API Error:', error)
    return ['Error generating conversation starters. Check your API key.']
  }
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

