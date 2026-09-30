import json, os, re
from openai import OpenAI
from services.cj import search_products, product_detail, variants, storefront_url

def _client(): return OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
def _json(text):
    text=text.strip().replace('```json','').replace('```','')
    return json.loads(text)

def research_trending_products():
    if not os.getenv('OPENAI_API_KEY'):
        return [{"name":f"Demo Product {i}","reason":"Add OPENAI_API_KEY to enable live AI web research.","trend_score":101-i,"supplier_search_query":"home gadget"} for i in range(1,6)]
    prompt='''Research ecommerce products showing strong consumer buying/demand momentum during roughly the last 14-30 days. Return exactly 5 physical, ad-friendly products. Avoid regulated/unsafe goods, weapons, alcohol, nicotine, gambling, adult goods, prescription/medical claims and counterfeits. For each return name, reason grounded in recent signals, trend_score 1-100, and supplier_search_query suitable for CJdropshipping. JSON only: {"products":[...]}. Never invent exact sales figures.'''
    r=_client().responses.create(model=os.getenv('OPENAI_MODEL','gpt-5.6-luna'),tools=[{'type':'web_search'}],input=prompt)
    return _json(r.output_text)['products']

def _margin_price(cost):
    try: cost=float(str(cost).split('-')[0])
    except: cost=10
    return round(max(cost*2.45,cost+12)+.01,2)

def build_product(candidate):
    q=candidate.get('supplier_search_query') or candidate.get('name')
    matches=search_products(q,8)
    if not matches: raise RuntimeError(f'No CJdropshipping products matched “{q}”. Try another candidate/search phrase.')
    # CJ listing count is a useful supplier-platform signal; final selection still requires admin review.
    best=max(matches,key=lambda x:(int(x.get('listedNum') or 0),int(x.get('warehouseInventoryNum') or 0)))
    pid=best['id']; detail=product_detail(pid); vs=variants(pid)
    if not vs: raise RuntimeError('CJ product has no orderable variants.')
    chosen=min(vs,key=lambda v:float(v.get('variantSellPrice') or 10**9))
    cost=float(chosen.get('variantSellPrice') or best.get('sellPrice') or 10)
    price=_margin_price(cost); compare=round(price*1.28+.01,2)
    raw_desc=re.sub('<[^>]+>',' ',str(detail.get('description') or best.get('description') or ''))
    copy={"tagline":"A smart everyday upgrade, selected for usefulness and value.","description":raw_desc[:650] or best.get('nameEn',''),"benefits":["Practical design for everyday use","Selected from an established fulfillment catalog","Secure checkout with tracked order processing"]}
    if os.getenv('OPENAI_API_KEY'):
        prompt=f'''Write elegant, factual conversion copy for this CJdropshipping product. Product: {best.get('nameEn')}. Supplier description: {raw_desc[:2500]}. Return JSON only with tagline (max 18 words), description (60-100 words), benefits (exactly 3 short strings). Do not invent reviews, certifications, scarcity, shipping times, guarantees, health claims, materials, or capabilities not present in the supplied facts.'''
        r=_client().responses.create(model=os.getenv('OPENAI_MODEL','gpt-5.6-luna'),input=prompt)
        copy.update(_json(r.output_text))
    images=detail.get('productImageSet') or []
    image=chosen.get('variantImage') or detail.get('bigImage') or best.get('bigImage') or ''
    if image and image not in images: images=[image]+images
    return {
      'name':best.get('nameEn') or candidate['name'],'tagline':copy['tagline'],'description':copy['description'],
      'price':price,'compare_at':compare,'currency':'usd','image':image,'images':images[:6],'benefits':copy['benefits'],
      'supplier':'CJdropshipping','supplier_url':storefront_url(pid),'supplier_cost':cost,'cj_pid':pid,
      'cj_sku':best.get('sku') or detail.get('productSku'),'cj_vid':chosen.get('vid'),'cj_variant_sku':chosen.get('variantSku'),
      'cj_variant_name':chosen.get('variantKey') or chosen.get('variantNameEn') or 'Default','cj_listed_num':best.get('listedNum',0),
      'source_note':'Product data and fulfillment identifiers imported from CJdropshipping API. Retail copy is admin-approved.'
    }
