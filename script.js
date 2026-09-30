// Bangle Bliss - Simple frontend using vanilla JS
// NOTE: This version expects local images in the `images/` folder inside the project.

const products = [
	{id:1,name:'Kashi Traditional Bangle',price:1299,category:'Traditional',size:'M',color:'red',availability:true,
		image:'https://images.pexels.com/photos/36406040/pexels-photo-36406040.jpeg?auto=compress&cs=tinysrgb&w=800',
		alt:'Vibrant display of traditional Indian bangles', description:'Handcrafted traditional bangle with glass and zari work.'},
	{id:2,name:'Rani Bridal Set',price:5999,category:'Bridal',size:'L',color:'pink',availability:true,
		image:'https://images.pexels.com/photos/9808451/pexels-photo-9808451.jpeg?auto=compress&cs=tinysrgb&w=800',
		alt:'Close-up photograph of bridal bangles and jewelry', description:'Ornate bridal bangle set with zirconia accents.'},
	{id:3,name:'Gold Plated Classic',price:2499,category:'Gold',size:'M',color:'gold',availability:true,
		image:'https://images.pexels.com/photos/37485314/pexels-photo-37485314.jpeg?auto=compress&cs=tinysrgb&w=800',
		alt:'Elegant gold bangles and jewelry on display', description:'Classic gold-plated bangle with polished finish.'},
	{id:4,name:'Silver Filigree',price:1799,category:'Silver',size:'S',color:'silver',availability:true,
		image:'https://images.pexels.com/photos/34021937/pexels-photo-34021937.jpeg?auto=compress&cs=tinysrgb&w=800',
		alt:'Colorful Indian bangles displayed on a stand (silver design)', description:'Delicate filigree silver bangle.'},
	{id:5,name:'Zari Designer Loop',price:3299,category:'Designer',size:'M',color:'multicolor',availability:true,
		image:'https://images.pexels.com/photos/10164658/pexels-photo-10164658.jpeg?auto=compress&cs=tinysrgb&w=800',
		alt:'Close-up of traditional colorful bracelets—designer details', description:'Designer bangle with zari embroidery.'},
	{id:6,name:'Mehendi Traditional',price:1399,category:'Traditional',size:'S',color:'green',availability:true,
		image:'https://images.pexels.com/photos/36406040/pexels-photo-36406040.jpeg?auto=compress&cs=tinysrgb&w=800',
		alt:'Traditional Indian bangles with rich colors', description:'Mehendi-inspired bangles with traditional motifs.'},
	{id:7,name:'Bridal Zirconia',price:6999,category:'Bridal',size:'L',color:'white',availability:false,
		image:'https://images.pexels.com/photos/9808451/pexels-photo-9808451.jpeg?auto=compress&cs=tinysrgb&w=800',
		alt:'Bridal bangle set with gemstone and zirconia details', description:'Premium bridal set with zirconia stones.'},
	{id:8,name:'Minimal Silver Band',price:999,category:'Silver',size:'M',color:'silver',availability:true,
		image:'https://images.pexels.com/photos/37485314/pexels-photo-37485314.jpeg?auto=compress&cs=tinysrgb&w=800',
		alt:'Minimal polished bangle with clean silhouette', description:'Everyday minimal silver band.'}
]

const imageFallback = 'https://images.pexels.com/photos/36406040/pexels-photo-36406040.jpeg?auto=compress&cs=tinysrgb&w=800'

let currentCategory = 'All'
let cart = {}

// DOM refs
const productsGrid = document.getElementById('productsGrid')
const searchInput = document.getElementById('searchInput')
const cartBtn = document.getElementById('cartBtn')
const cartCount = document.getElementById('cartCount')
const cartPanel = document.getElementById('cartPanel')
const cartItemsEl = document.getElementById('cartItems')
const cartTotalEl = document.getElementById('cartTotal')
const closeCartBtn = document.getElementById('closeCart')
const heroShop = document.getElementById('heroShop')

// Chatbot
const chatToggle = document.getElementById('chatToggle') // floating bubble
const chatToggleHeader = document.getElementById('chatToggleHeader') // header button
const chatWindow = document.getElementById('chatWindow')
const closeChat = document.getElementById('closeChat')
const chatMessages = document.getElementById('chatMessages')
const chatInput = document.getElementById('chatInput')
const sendChat = document.getElementById('sendChat')

// Add quick suggestion buttons to chatbot header
function addChatSuggestions(){
	const header = document.querySelector('.chat-header')
	if(!header) return
	const container = document.createElement('div')
	container.className = 'chat-suggestions'
	container.innerHTML = `
		<button class="sugg">❤️ Red bangles</button>
		<button class="sugg">💰 Under ₹500</button>
		<button class="sugg">💍 Bridal styles</button>
		<button class="sugg">✨ Traditional bangles</button>
	`
	container.addEventListener('click', (e)=>{
		const b = e.target.closest('button')
		if(b){
			chatInput.value = b.textContent.replace(/^[^\s]+\s*/, '')
			sendChat.click()
		}
	})
	header.appendChild(container)
}

setTimeout(addChatSuggestions, 400)

// Backend endpoint for local Flask proxy
const BACKEND_CHAT = 'http://localhost:5000/api/chat'

function renderProducts(){
	const q = (searchInput.value || '').toLowerCase().trim()
	const list = products.filter(p => (currentCategory==='All' || p.category===currentCategory) && (p.name.toLowerCase().includes(q) || (p.description||'').toLowerCase().includes(q)))
	productsGrid.innerHTML = ''
	list.forEach(p => {
		const card = document.createElement('article')
		card.className = 'product-card'
		card.innerHTML = `
			<div class="product-image"><img src="${p.image}" alt="${p.alt}" onerror="this.onerror=null;this.parentNode.classList.add('img-missing');this.src='${imageFallback}'"/></div>
			<div>
				<div class="meta"><div class="title">${p.name}</div><div class="price">₹${p.price}</div></div>
				<div class="meta"><div class="muted">${p.category} ${p.color?('• '+p.color):''}</div><div class="muted">Size: ${p.size}</div></div>
				<div class="desc" style="margin-top:6px;color:var(--muted);font-size:0.95rem">${p.description||''}</div>
			</div>
			<div class="product-actions">
				<button class="wishlist" aria-label="Add to wishlist">♡</button>
				<button class="add-cart" data-id="${p.id}" aria-label="Add to cart">Add to Cart</button>
			</div>
		`
		productsGrid.appendChild(card)
	})
	document.querySelectorAll('.add-cart').forEach(btn=>btn.addEventListener('click', ()=>addToCart(Number(btn.dataset.id))))
	document.querySelectorAll('.wishlist').forEach(w=>w.addEventListener('click', ()=>{ w.textContent = w.textContent==='♡' ? '♥' : '♡' }))
}

document.querySelectorAll('.cat-btn').forEach(btn=>btn.addEventListener('click', ()=>{
	document.querySelectorAll('.cat-btn').forEach(b=>b.classList.remove('active'))
	btn.classList.add('active')
	currentCategory = btn.dataset.cat
	renderProducts()
}))

searchInput.addEventListener('input', ()=>renderProducts())

function saveCart(){try{localStorage.setItem('bb_cart', JSON.stringify(cart))}catch(e){}
}
function loadCart(){try{cart = JSON.parse(localStorage.getItem('bb_cart'))||{}}catch(e){cart={}}
}

function addToCart(id){cart[id]=(cart[id]||0)+1;updateCartUI();saveCart()}
function changeQty(id,delta){cart[id]=(cart[id]||0)+delta;if(cart[id]<=0)delete cart[id];updateCartUI();saveCart()}
function removeFromCart(id){delete cart[id];updateCartUI();saveCart()}

function updateCartUI(){
	const itemCount = Object.values(cart).reduce((s,n)=>s+n,0)
	cartCount.textContent = itemCount
	cartItemsEl.innerHTML = ''
	let total = 0
	for(const idStr of Object.keys(cart)){
		const id = Number(idStr), qty = cart[id]
		const p = products.find(x=>x.id===id); if(!p) continue
		const row = document.createElement('div'); row.className='cart-item'
		row.innerHTML = `
			<div class="thumb"><img src="${p.image}" alt="${p.alt}" onerror="this.onerror=null;this.src='${imageFallback}'"/></div>
			<div style="flex:1">
				<div style="font-weight:600">${p.name}</div>
				<div style="color:var(--muted);font-size:0.9rem">Size: ${p.size} • ₹${p.price}</div>
				<div class="qty-controls" style="margin-top:6px">
					<button class="btn" data-action="dec" data-id="${id}">-</button>
					<div style="padding:0 0.5rem">${qty}</div>
					<button class="btn" data-action="inc" data-id="${id}">+</button>
					<button class="btn" data-action="rem" data-id="${id}" style="margin-left:8px">Remove</button>
				</div>
			</div>
		`
		cartItemsEl.appendChild(row)
		total += p.price*qty
	}
	cartTotalEl.textContent = `₹${total}`
	cartItemsEl.querySelectorAll('button[data-action]').forEach(btn=>{
		const id = Number(btn.dataset.id), action = btn.dataset.action
		btn.addEventListener('click', ()=>{ if(action==='inc') changeQty(id,1); if(action==='dec') changeQty(id,-1); if(action==='rem') removeFromCart(id) })
	})
}

cartBtn.addEventListener('click', ()=>{cartPanel.classList.toggle('open');cartPanel.setAttribute('aria-hidden', String(!cartPanel.classList.contains('open')))})
closeCartBtn.addEventListener('click', ()=>{cartPanel.classList.remove('open');cartPanel.setAttribute('aria-hidden','true')})

function toggleChat(){ const open = chatWindow.getAttribute('aria-hidden')==='true'; chatWindow.setAttribute('aria-hidden', String(!open)); chatWindow.style.display = open ? 'flex' : 'none' }
if(chatToggle) chatToggle.addEventListener('click', toggleChat)
if(chatToggleHeader) chatToggleHeader.addEventListener('click', toggleChat)
closeChat.addEventListener('click', ()=>{chatWindow.setAttribute('aria-hidden','true');chatWindow.style.display='none'})
sendChat.addEventListener('click', async ()=>{
	const txt = (chatInput.value||'').trim()
	if(!txt) return
	appendChat('user', txt)
	chatInput.value = ''

	// show loading indicator message
	const loadingId = appendChat('bot', '…')
	try{
		const resp = await fetch(BACKEND_CHAT, {
			method: 'POST',
			headers: {'Content-Type':'application/json'},
			body: JSON.stringify({message: txt})
		})
		if(!resp.ok){
			// Try to parse error details but show a friendly message to the user
			const err = await resp.json().catch(()=>({error:resp.statusText}))
			console.error('Chat backend error:', err)
			updateChatMessage(loadingId, "Sorry — the assistant is temporarily unavailable. You can still search for products using the search box or try again in a moment.")
			return
		}
		const data = await resp.json()
		// Expecting Flask to return { response: "clean assistant response" }
		const reply = data.response || data.reply

		// Handle short greeting/local replies quickly without involving Llama further
		const simple = (txt)=>{
			const s = (txt||'').toLowerCase().trim()
			if(['hi','hello','hey','thanks','thank you','bye','goodbye'].includes(s)) return true
			return false
		}
		if(simple((chatInput.value||'').trim())){
			// map to short friendly replies
			const m = (chatInput.value||'').toLowerCase()
			if(m.includes('hi')||m.includes('hello')||m.includes('hey')){ updateChatMessage(loadingId, "Hey! 👋 How can I help you with Bangle Bliss today?"); return }
			if(m.includes('thank')){ updateChatMessage(loadingId, "You're welcome! Glad to help."); return }
			if(m.includes('bye')||m.includes('goodbye')){ updateChatMessage(loadingId, "Goodbye! Come back anytime."); return }
		}
		if(reply === 'search_results' && Array.isArray(data.products)){
			updateChatMessage(loadingId, 'Here are some items I found:')
			renderProductsInChat(data.products, loadingId)
			return
		}
		if(reply && typeof reply === 'string'){
			updateChatMessage(loadingId, reply)
		}else{
			console.warn('Empty reply from backend', data)
			updateChatMessage(loadingId, "Sorry — the assistant didn't return a reply. You can still browse products or try again.")
		}
	}catch(err){
		// Log the real error for debugging, but show a friendly message to users
		console.error('Chat request failed', err)
		updateChatMessage(loadingId, "Sorry — the chat service is currently unavailable. Please try again later or use the search to find products.")
	}
})

function appendChat(who,text){
	const el=document.createElement('div')
	el.className = who==='user'?'user-msg':'bot-msg'
	el.style.margin='6px 0'
	el.textContent=text
	chatMessages.appendChild(el)
	chatMessages.scrollTop=chatMessages.scrollHeight
	// return element id (use timestamp) for updates
	const id = 'm-'+Date.now()
	el.dataset.id = id
	return id
}

function updateChatMessage(id, text){
	const el = Array.from(chatMessages.children).find(c=>c.dataset.id===id)
	if(el){ el.textContent = text }
}


function updateChatMessageHTML(id, html){
	const el = Array.from(chatMessages.children).find(c=>c.dataset.id===id)
	if(el){ el.innerHTML = html }
}


function renderProductsInChat(list, loadingId){
	// Insert a container after the loading message
	const container = document.createElement('div')
	container.className = 'chat-product-list'
	container.style.display = 'grid'
	container.style.gridTemplateColumns = 'repeat(auto-fit, minmax(180px, 1fr))'
	container.style.gap = '10px'
	container.style.marginTop = '8px'

	list.forEach(p=>{
		const card = document.createElement('article')
		card.className = 'product-card chat-card'
		card.innerHTML = `
			<div class="product-image"><img src="${p.image}" alt="${p.alt||p.name}" onerror="this.onerror=null;this.src='${imageFallback}'"/></div>
			<div>
				<div class="meta"><div class="title">${p.name}</div><div class="price">₹${p.price}</div></div>
				<div class="meta"><div class="muted">${p.category}</div><div class="muted">Size: ${p.size||'—'}</div></div>
			</div>
			<div class="product-actions">
				<button class="btn chat-add" data-id="${p.id}">Add to Cart</button>
			</div>
		`
		container.appendChild(card)
	})

	// Replace loading text with HTML and append the product container
	updateChatMessageHTML(loadingId, '')
	const el = Array.from(chatMessages.children).find(c=>c.dataset.id===loadingId)
	if(el){ el.appendChild(container) }

	// Wire up add-to-cart buttons inside chat
	container.querySelectorAll('.chat-add').forEach(btn=>{
		btn.addEventListener('click', ()=>{
			const id = Number(btn.dataset.id)
			addToCart(id)
			// provide inline confirmation
			btn.textContent = 'Added'
			setTimeout(()=>btn.textContent='Add to Cart',800)
		})
	})
}

heroShop.addEventListener('click', (e)=>{e.preventDefault();document.getElementById('shop').scrollIntoView({behavior:'smooth'})})

loadCart(); renderProducts(); updateCartUI()

