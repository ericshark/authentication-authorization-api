import Joke from "./Joke.jsx"
import data from "./data.js"
export default function App() {
    return (
               <>
        {data.map((object) =>{
            return <Joke
                key={object.punchline}
                {...object}
            />
        })}

        </>
    )
}
