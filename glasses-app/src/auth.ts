import { createRemoteJWKSet, decodeProtectedHeader, errors, jwtVerify, type JWTPayload } from 'jose';
import 'dotenv/config';

const SUPABASE_URL = process.env.SUPABASE_URL?.trim();
const SUPABASE_JWT_SECRET = process.env.SUPABASE_JWT_SECRET?.trim();

if (!SUPABASE_URL) {
  throw new Error('SUPABASE_URL is required for JWT verification');
}

const ISSUER = `${SUPABASE_URL.replace(/\/$/, '')}/auth/v1`;
const AUDIENCE = 'authenticated';
const JWKS = createRemoteJWKSet(new URL(`${ISSUER}/.well-known/jwks.json`));

export class AuthError extends Error {
  readonly statusCode: number;

  constructor(message: string, statusCode = 401) {
    super(message);
    this.name = 'AuthError';
    this.statusCode = statusCode;
  }
}

export type VerifiedJwtPayload = JWTPayload & {
  sub: string;
  email?: string | null;
};

function asVerifiedPayload(payload: JWTPayload): VerifiedJwtPayload {
  if (!payload.sub || typeof payload.sub !== 'string') {
    throw new AuthError('Invalid token: missing user ID');
  }
  return payload as VerifiedJwtPayload;
}

export function extractTokenFromQueryParams(
  query?: string | URL | URLSearchParams | null,
  tokenParamNames: readonly string[] = ['access_token', 'token'],
): string | null {
  if (!query) {
    return null;
  }

  let searchParams: URLSearchParams;
  if (query instanceof URLSearchParams) {
    searchParams = query;
  } else if (query instanceof URL) {
    searchParams = query.searchParams;
  } else {
    const value = query.trim();
    if (!value) {
      return null;
    }

    try {
      searchParams = new URL(value).searchParams;
    } catch {
      try {
        searchParams = new URL(value, 'http://localhost').searchParams;
      } catch {
        searchParams = new URLSearchParams(value.startsWith('?') ? value.slice(1) : value);
      }
    }
  }

  for (const paramName of tokenParamNames) {
    const token = searchParams.get(paramName)?.trim();
    if (token) {
      return token;
    }
  }
  return null;
}

export async function verifyJwt(token: string): Promise<VerifiedJwtPayload> {
  let alg: string | undefined;

  try {
    alg = decodeProtectedHeader(token).alg;

    if (alg === 'HS256') {
      if (!SUPABASE_JWT_SECRET) {
        throw new AuthError('SUPABASE_JWT_SECRET is required to verify HS256 tokens');
      }

      const { payload } = await jwtVerify(token, new TextEncoder().encode(SUPABASE_JWT_SECRET), {
        algorithms: ['HS256'],
        audience: AUDIENCE,
      });
      return asVerifiedPayload(payload);
    }

    if (alg === 'ES256' || alg === 'RS256') {
      const { payload } = await jwtVerify(token, JWKS, {
        algorithms: [alg],
        audience: AUDIENCE,
        issuer: ISSUER,
      });
      return asVerifiedPayload(payload);
    }

    throw new AuthError(`Invalid token: unsupported algorithm ${alg ?? 'unknown'}`);
  } catch (err) {
    if (err instanceof AuthError) {
      throw err;
    }

    if (err instanceof errors.JWTExpired) {
      throw new AuthError('Token has expired');
    }

    if (
      err instanceof errors.JWSSignatureVerificationFailed ||
      err instanceof errors.JWTClaimValidationFailed ||
      err instanceof errors.JWTInvalid ||
      err instanceof errors.JOSEError
    ) {
      throw new AuthError(`Invalid token: ${err.message}`);
    }

    throw new AuthError('Invalid token');
  }
}
