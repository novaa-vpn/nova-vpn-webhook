export default async function handler(req,res){

try{

let r = await fetch("https://api.coingecko.com/api/v3/simple/price?ids=tether&vs_currencies=usd")
let data = await r.json()

res.json({
  price: data.tether.usd
})

}catch(e){
res.status(500).json({error:"price error"})
}

}
