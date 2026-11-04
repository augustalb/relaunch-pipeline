export type Sourced = { value: string; source: string; snippet?: string | null };
export type ServiceItem = { name: Sourced; description?: string | null; price?: Sourced | null };
export type PriceItem = { label: Sourced; price: Sourced };
export type HoursBlock = { label: string; entries: Sourced[] };
export type TeamMember = { name: Sourced; role?: string | null };
export type Contact = { phone?: Sourced | null; email?: Sourced | null; address?: Sourced | null; whatsapp?: Sourced | null };
export type ImageRef = { url: string; alt: string; role: 'logo' | 'hero' | 'gallery' };

export type SiteContent = {
  industry: string;
  company_name: Sourced;
  city?: string | null;
  tagline: string;
  hero_text: string;
  cta_primary: string;
  highlights: string[];
  about?: string | null;
  services: ServiceItem[];
  prices: PriceItem[];
  price_note?: string | null;
  hours: HoursBlock[];
  team: TeamMember[];
  contact: Contact;
  images: ImageRef[];
  hero_image?: string | null;
};

export type PreviewMeta = {
  slug: string;
  company: string;
  sender_name: string;
  brand_name: string;
  reply_to: string;
  old_website?: string;
  imprint_url?: string | null;
  privacy_url?: string | null;
  palette?: string;
  created_at: string;
  mode: 'preview' | 'production';
};

export type PreviewFile = { meta: PreviewMeta; content: SiteContent };
