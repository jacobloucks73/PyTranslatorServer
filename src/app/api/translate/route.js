// /app/api/translate/route.js
// import OpenAI from "openai";
// import { NextResponse } from "next/server";
// import { useSearchParams } from "next/navigation";


// // TO DO : 
// // 
// // condense copypasta to variable input 
// // input lan variable from URL into lan var
// // obfusacate the API key 
// // 
// // 


// const openai = new OpenAI({
//   apiKey:  process.env.REACT_APP_API_KEY,
// });

//   const searchParams = useSearchParams();
//   const lan = searchParams.get("lan"); // "host" or "viewer"

// export async function POST(req) {
//   try {
//     const { text } = await req.json();

//     if (!text || text.trim().length === 0) {
//       return NextResponse.json({ error: "No text provided" }, { status: 400 });
//     }
//     if (lan == "es"){ //spanish
//     const completion = await openai.chat.completions.create({
//       model: "gpt-4o-mini",
//       messages: [
//         {
//           role: "system",
//           content: "You are a real-time translator. Translate the user's text to Spanish naturally.",
//         },
//         { role: "user", content: text },
//       ],
//     });
//     }
//     else if (lan == "de"){  //German
//     const completion = await openai.chat.completions.create({
//       model: "gpt-4o-mini",
//       messages: [
//         {
//           role: "system",
//           content: "You are a real-time translator. Translate the user's text to German naturally.",
//         },
//         { role: "user", content: text },
//       ],
//     });
//     }
//     else if (lan == "fr"){  //French
//     const completion = await openai.chat.completions.create({
//       model: "gpt-4o-mini",
//       messages: [
//         {
//           role: "system",
//           content: "You are a real-time translator. Translate the user's text to French naturally.",
//         },
//         { role: "user", content: text },
//       ],
//     });
//     }
//     else if (lan == "it"){  //Italian
//     const completion = await openai.chat.completions.create({
//       model: "gpt-4o-mini",
//       messages: [
//         {
//           role: "system",
//           content: "You are a real-time translator. Translate the user's text to Italian naturally.",
//         },
//         { role: "user", content: text },
//       ],
//     });
//     }
//     else if (lan == "en"){  //English
//     const completion = await openai.chat.completions.create({
//       model: "gpt-4o-mini",
//       messages: [
//         {
//           role: "system",
//           content: "You are a real-time translator. Translate the user's text to English naturally.",
//         },
//         { role: "user", content: text },
//       ],
//     });
//     }
//     else if (lan == "ha"){  //Haitian Creole
//     const completion = await openai.chat.completions.create({
//       model: "gpt-4o-mini",
//       messages: [
//         {
//           role: "system",
//           content: "You are a real-time translator. Translate the user's text to Haitian Creole naturally.",
//         },
//         { role: "user", content: text },
//       ],
//     });
//     }
//     // else {return NextResponse.json({ error: "language variable not valid/found in Translate/route.js" }, { status: 400 }} fix this line to add error checking, too lazy to add syntax right now 

//     const translation = completion.choices?.[0]?.message?.content || "";

//     return NextResponse.json({ translation });
//   } catch (error) {
//     console.error("Translation error:", error);
//     return NextResponse.json(
//       { error: "Translation failed", details: error.message },
//       { status: 500 }
//     );
//   }
// }


import OpenAI from "openai";
import { NextResponse } from "next/server";

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY, // ✅ safer and standard env var
});

export async function POST(req) {
  try {
    const { text, lan } = await req.json();

    if (!text?.trim()) {
      return NextResponse.json({ error: "No text provided" }, { status: 400 });
    }

    if (!lan) {
      return NextResponse.json({ error: "Missing target language" }, { status: 400 });
    }

    // Build system message dynamically
    const languageMap = {
      es: "Spanish",
      de: "German",
      fr: "French",
      it: "Italian",
      en: "English",
      ha: "Haitian Creole",
    };

    const targetLanguage = languageMap[lan];
    if (!targetLanguage) {
      return NextResponse.json({ error: `Unsupported language: ${lan}` }, { status: 400 });
    }

    const completion = await openai.chat.completions.create({
      model: "gpt-4o-mini",
      messages: [
        {
          role: "system",
          content: `You are a real-time translator. Translate the user's text to ${targetLanguage} naturally.`,
        },
        { role: "user", content: text },
      ],
    });

    const translation = completion.choices?.[0]?.message?.content || "";
    return NextResponse.json({ translation });
  } catch (error) {
    console.error("Translation error:", error);
    return NextResponse.json(
      { error: "Translation failed", details: error.message },
      { status: 500 }
    );
  }
}



  // speech → WebSocket → DB (raw text) → Punctuation → Translation → DB (updated, multilingual, punctuated)